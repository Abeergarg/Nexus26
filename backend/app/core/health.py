"""
Health check endpoints for Project Nexus26.

Provides two probes:
  - /health/live  — Liveness: is the process alive?
  - /health/ready — Readiness: are all dependencies operational?
"""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])

APP_VERSION = "2.1.0"


@router.get(
    "/health/live",
    summary="Liveness Probe",
    description="Returns 200 if the server process is running. Used by orchestrators to detect crashes.",
)
def liveness() -> dict:
    """
    Liveness probe.

    Always returns 200 as long as the Python process is alive.
    No dependency checks are performed here.
    """
    return {"status": "alive", "version": APP_VERSION}


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description=(
        "Returns 200 if all internal dependencies are operational. "
        "Returns 503 if any critical component is unavailable."
    ),
)
def readiness() -> dict:
    """
    Readiness probe.

    Checks:
    - Topology graph loaded (routing service has nodes)
    - Cache operational (SimulatedRedis responds)
    - Config accessible (settings object is valid)
    """
    from app.features.wayfinding.service import routing_service
    from app.core.cache import redis_client
    from fastapi.responses import JSONResponse

    checks: dict = {}
    overall_ok = True

    # 1. Topology check
    topology_ok = bool(routing_service.nodes)
    checks["topology"] = "ok" if topology_ok else "degraded"
    if not topology_ok:
        overall_ok = False

    # 2. Cache check
    try:
        redis_client.get_stats()
        checks["cache"] = "ok"
    except Exception:
        checks["cache"] = "degraded"
        overall_ok = False

    # 3. Config check
    try:
        _ = settings.HOST
        checks["config"] = "ok"
    except Exception:
        checks["config"] = "degraded"
        overall_ok = False

    payload = {
        "status": "ready" if overall_ok else "degraded",
        "version": APP_VERSION,
        "components": checks,
    }

    if not overall_ok:
        return JSONResponse(status_code=503, content=payload)

    return payload
