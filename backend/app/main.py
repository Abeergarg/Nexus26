"""
Project Nexus26 — FastAPI Application Entry Point.

Configures:
  - CORS, rate limiting, request ID propagation, request logging.
  - Centralized exception handling and Pydantic validation error mapping.
  - Feature routers: wayfinding, telemetry, operations.
  - Health check endpoints.
  - Background crowd telemetry simulation thread (started via lifespan).
"""

import random
import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.constants import DENSITY_MIN, DENSITY_MAX
from app.core.exceptions import GlobalExceptionMiddleware, validation_exception_handler
from app.core.health import router as health_router
from app.core.logging import get_structured_logger
from app.core.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
    RateLimitMiddleware,
)
from app.features.operations.router import router as operations_router
from app.features.telemetry.router import router as telemetry_router
from app.features.wayfinding.router import router as wayfinding_router
from app.features.wayfinding.service import routing_service

logger = get_structured_logger("NexusCore")


# ---------------------------------------------------------------------------
# Background Telemetry Simulation
# ---------------------------------------------------------------------------


def _run_crowd_telemetry_simulation() -> None:
    """
    Background worker thread that periodically updates crowd density on random
    topological edges to simulate live game-day congestion patterns.

    Runs as a daemon thread — terminates automatically when the main process exits.
    """
    logger.info("Background Telemetry Simulator Thread started.")

    edges_to_simulate = [
        (edge["source"], edge["target"])
        for node_edges in routing_service.adj.values()
        for edge in node_edges
    ]

    if not edges_to_simulate:
        logger.warning("No topological edges found — telemetry simulation skipped.")
        return

    while True:
        num_updates = random.randint(3, 6)
        selected_edges = random.sample(
            edges_to_simulate, min(len(edges_to_simulate), num_updates)
        )

        updated_details = []
        for source, target in selected_edges:
            density = round(random.uniform(DENSITY_MIN, DENSITY_MAX), 2)
            routing_service.update_edge_density(source, target, density)
            updated_details.append(
                {"source": source, "target": target, "density": density}
            )

        logger.info(
            f"Telemetry simulation tick: updated {num_updates} edge densities.",
            extra={"updated_edges": updated_details},
        )
        time.sleep(settings.TELEMETRY_SIM_INTERVAL)


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern lifespan context manager — replaces deprecated @app.on_event."""
    logger.info("Nexus26 starting up — launching background telemetry simulator.")
    sim_thread = threading.Thread(target=_run_crowd_telemetry_simulation, daemon=True)
    sim_thread.start()
    yield
    logger.info("Nexus26 shutting down gracefully.")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Project Nexus26: Stadium Operations Core",
    version="2.1.0",
    description=(
        "Intelligent Stadium Operations API for FIFA World Cup 2026 Virtual Edition. "
        "Features: real-time wayfinding, crowd telemetry, operational forecasting, "
        "semantic caching, PII scrubbing, multilingual routing."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Wayfinding",
            "description": "Dijkstra-based route calculation with accessibility profiles.",
        },
        {
            "name": "Telemetry",
            "description": "Stadium topology and real-time crowd density ingestion.",
        },
        {
            "name": "Operations",
            "description": "Resource forecasting, heat index analysis, and supply management.",
        },
        {
            "name": "Health",
            "description": "Liveness and readiness probes for production monitoring.",
        },
    ],
)

# Middleware registration order matters: outermost runs first on request, last on response.
# RequestID must be first so all downstream middleware/handlers can read the request ID.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(GlobalExceptionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Routers
app.include_router(health_router)
app.include_router(wayfinding_router, prefix="/api/navigation", tags=["Wayfinding"])
app.include_router(telemetry_router, prefix="/api/telemetry", tags=["Telemetry"])
app.include_router(operations_router, prefix="/api/operations", tags=["Operations"])


# ---------------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Returns project metadata and available API routes.",
)
def root() -> dict:
    """API root — returns project metadata and available endpoints."""
    return {
        "project": "Project Nexus26 (Virtual Edition)",
        "venue": "MetLife Stadium Virtual (FIFA World Cup 2026)",
        "status": "OPERATIONAL",
        "version": "2.1.0",
        "apis": {
            "topology": "/api/telemetry/topology",
            "navigation": "/api/navigation/route [POST]",
            "telemetry": "/api/telemetry/simulate [POST]",
            "forecasting": "/api/operations/forecast [GET]",
            "replenish": "/api/operations/replenish [POST]",
            "cache_stats": "/api/operations/cache/stats [GET]",
            "health_live": "/health/live [GET]",
            "health_ready": "/health/ready [GET]",
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
