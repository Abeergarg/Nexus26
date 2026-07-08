"""
Operations API router for Project Nexus26.

Endpoints:
  - GET  /api/operations/forecast    — Live resource & heat index forecast.
  - POST /api/operations/replenish   — Restock supplies (Administrator only).
  - GET  /api/operations/cache/stats — Cache hit/miss performance metrics.
"""

import random
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.cache import redis_client
from app.core.logging import get_structured_logger
from app.features.operations.models import ForecastResponse, ReplenishResponse
from app.features.operations.service import forecasting_service
from app.features.operations.weather import get_external_weather

router = APIRouter()
logger = get_structured_logger("OperationsRouter")

# Attendance simulation range (MetLife Stadium capacity: 82,500)
_ATTENDANCE_MIN: int = 62_000
_ATTENDANCE_MAX: int = 78_000


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Live Operations Forecast",
    description=(
        "Returns current heat indexes, resource depletion warnings, and automated dispatch "
        "recommendations using cached async weather API lookups."
    ),
    response_description="Forecast payload including heat metrics, alerts, and dispatch actions.",
)
async def get_operations_forecast(
    attendance: Optional[int] = Query(
        None, ge=0, le=200_000, description="Current venue occupancy"
    ),
    temp_c: Optional[float] = Query(
        None, ge=-50.0, le=60.0, description="Manual temperature override (°C)"
    ),
    humidity: Optional[float] = Query(
        None, ge=0.0, le=100.0, description="Manual humidity override (%)"
    ),
) -> ForecastResponse:
    """
    Fetches current weather (with cache and fallback), simulates a depletion tick,
    and returns a full operational forecast with alerts and dispatch actions.
    """
    forecasting_service.simulate_tick()

    if temp_c is None or humidity is None:
        api_temp, api_humidity = await get_external_weather()
        if temp_c is None:
            temp_c = api_temp
        if humidity is None:
            humidity = api_humidity

    if attendance is None:
        attendance = random.randint(_ATTENDANCE_MIN, _ATTENDANCE_MAX)

    logger.info(
        "Generating operations forecast.",
        extra={"attendance": attendance, "temp_c": temp_c, "humidity": humidity},
    )

    forecast = forecasting_service.generate_live_operations_forecast(
        attendance=attendance, current_temp_c=temp_c, current_humidity=humidity
    )
    forecast["inputs"] = {
        "attendance": attendance,
        "temperature_celsius": temp_c,
        "humidity_percentage": humidity,
    }
    return forecast


@router.post(
    "/replenish",
    response_model=ReplenishResponse,
    summary="Replenish All Supplies",
    description="Restocks all stadium supplies to near-peak capacity. Requires Administrator role.",
    response_description="Confirmation that all resources have been replenished.",
)
def replenish_supplies(
    x_user_role: str = Header(
        "Volunteer", description="Simulated RBAC role (Administrator required)"
    ),
) -> ReplenishResponse:
    """
    Triggers a full supply replenishment event.

    Protected by RBAC: only the ``Administrator`` role may call this endpoint.
    Returns HTTP 403 Forbidden for any other role.
    """
    if x_user_role != "Administrator":
        logger.warning(
            "Unauthorized replenish attempt.",
            extra={"role": x_user_role},
        )
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only Administrator role can replenish supply inventories.",
        )

    forecasting_service.trigger_replenish()
    logger.info("Supply replenishment triggered by Administrator.")
    return {
        "status": "success",
        "message": "All stadium resources restocked to peak capacity.",
    }


@router.get(
    "/cache/stats",
    summary="Cache Performance Metrics",
    description="Exposes cache hit rate, miss count, and total query volume for the semantic cache.",
)
def get_cache_stats() -> dict:
    """Returns performance telemetry from the SimulatedRedis semantic cache."""
    return redis_client.get_stats()
