import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import threading
import time
import random

# Import Core Layer
from app.core.config import settings
from app.core.logging import get_structured_logger
from app.core.exceptions import GlobalExceptionMiddleware, validation_exception_handler

# Import Features Layer
from app.features.wayfinding.router import router as wayfinding_router
from app.features.wayfinding.service import routing_service
from app.features.telemetry.router import router as telemetry_router
from app.features.operations.router import router as operations_router

logger = get_structured_logger("NexusCore")

app = FastAPI(
    title="Project Nexus26: Stadium Operations Core",
    version="2.0.0",
    description="Intelligent Stadium Operations API for FIFA World Cup 2026 Virtual Edition (Production Grade)",
)

# Register CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Centralized Error Handling Middleware
app.add_middleware(GlobalExceptionMiddleware)

# Register DTO Validation Exception Handler (Type-Safety)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Register Feature Routers
app.include_router(wayfinding_router, prefix="/api/navigation", tags=["Wayfinding"])
app.include_router(telemetry_router, prefix="/api/telemetry", tags=["Telemetry"])
app.include_router(operations_router, prefix="/api/operations", tags=["Operations"])


@app.get("/", tags=["Root"])
def root():
    return {
        "project": "Project Nexus26 (Virtual Edition)",
        "venue": "MetLife Stadium Virtual (FIFA World Cup 2026)",
        "status": "OPERATIONAL",
        "apis": {
            "topology": "/api/telemetry/topology",
            "navigation": "/api/navigation/route [POST]",
            "telemetry": "/api/telemetry/simulate [POST]",
            "forecasting": "/api/operations/forecast [GET]",
            "replenish": "/api/operations/replenish [POST]",
            "cache_stats": "/api/operations/cache/stats [GET]",
        },
    }


# --- Background Telemetry Simulator Thread ---


def run_crowd_telemetry_simulation():
    """
    Background worker thread. Periodically updates crowd levels of random topological edges
    to simulate crowd movements, game pauses, halftime congestion, and general flow spikes.
    """
    logger.info("Background Telemetry Simulator Thread Started.")

    # Compile list of edges to simulate
    edges_to_simulate = []
    for node_edges in routing_service.adj.values():
        for edge in node_edges:
            edges_to_simulate.append((edge["source"], edge["target"]))

    if not edges_to_simulate:
        logger.warning("No topological edges found to simulate telemetry on.")
        return

    while True:
        num_updates = random.randint(3, 6)
        selected_edges = random.sample(
            edges_to_simulate, min(len(edges_to_simulate), num_updates)
        )

        updated_details = []
        for source, target in selected_edges:
            density = round(random.uniform(0.05, 0.95), 2)
            routing_service.update_edge_density(source, target, density)
            updated_details.append(
                {"source": source, "target": target, "density": density}
            )

        logger.info(
            f"Ingested simulated telemetry loop: Updated {num_updates} edge densities.",
            extra={"updated_edges": updated_details},
        )
        time.sleep(settings.TELEMETRY_SIM_INTERVAL)


@app.on_event("startup")
def start_simulator():
    """Starts the background simulation loop on server startup."""
    sim_thread = threading.Thread(target=run_crowd_telemetry_simulation, daemon=True)
    sim_thread.start()


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
