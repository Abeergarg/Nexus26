from fastapi import APIRouter, Query, Header, HTTPException
from typing import Optional
import random

from app.features.operations.models import ForecastResponse
from app.features.operations.service import forecasting_service
from app.features.operations.weather import get_external_weather
from app.core.cache import redis_client

router = APIRouter()


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    description=(
        "Returns the current heat indexes, resource warnings, and dispatches, "
        "using cached async weather API lookups."
    ),
)
async def get_operations_forecast(
    attendance: Optional[int] = Query(None, description="Current venue occupancy"),
    temp_c: Optional[float] = Query(
        None, description="Manually override temperature (C)"
    ),
    humidity: Optional[float] = Query(None, description="Manually override humidity %"),
):
    # Simulate time step depletion tick
    forecasting_service.simulate_tick()

    # 1. Weather gathering (use async external API with fallback if not manually overridden)
    if temp_c is None or humidity is None:
        api_temp, api_humidity = await get_external_weather()
        if temp_c is None:
            temp_c = api_temp
        if humidity is None:
            humidity = api_humidity

    if attendance is None:
        attendance = random.randint(62000, 78000)

    # 2. Run forecast algorithms
    forecast = forecasting_service.generate_live_operations_forecast(
        attendance=attendance, current_temp_c=temp_c, current_humidity=humidity
    )

    # Pack inputs for response
    forecast["inputs"] = {
        "attendance": attendance,
        "temperature_celsius": temp_c,
        "humidity_percentage": humidity,
    }
    return forecast


@router.post(
    "/replenish", description="Replenishes stadium supplies to peak 100% capacity."
)
def replenish_supplies(
    x_user_role: str = Header("Volunteer", description="Simulated RBAC Role")
):
    if x_user_role != "Administrator":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only Administrator role can replenish supply inventories.",
        )
    forecasting_service.trigger_replenish()
    return {
        "status": "success",
        "message": "All stadium resources restocked to peak capacity.",
    }


@router.get(
    "/cache/stats", description="Exposes cache performance and hit ratio metrics."
)
def get_cache_stats():
    return redis_client.get_stats()
