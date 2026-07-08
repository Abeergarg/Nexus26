"""
Telemetry API router for Project Nexus26.

Endpoints:
  - GET  /api/telemetry/topology  — Stadium topology graph (nodes + edges).
  - POST /api/telemetry/simulate  — Ingest real-time hardware telemetry events.
"""

from fastapi import APIRouter

from app.core.logging import get_structured_logger
from app.features.telemetry.models import TelemetryStream
from app.features.wayfinding.service import routing_service

router = APIRouter()
logger = get_structured_logger("TelemetryRouter")


@router.get(
    "/topology",
    summary="Stadium Topology Graph",
    description=(
        "Returns the static node definitions and dynamic bidirectional edge crowd density graph "
        "for MetLife Stadium. Used by the frontend to render the SVG wayfinding map."
    ),
)
def get_topology() -> dict:
    """
    Returns the full stadium topology graph.

    Includes all node definitions (gates, sections, amenities, transit) and
    all directional edges with current crowd density values.
    """
    node_count = len(routing_service.nodes)
    logger.info("Topology graph requested.", extra={"node_count": node_count})

    edges = [
        {
            "source": edge["source"],
            "target": edge["target"],
            "distance": edge["distance"],
            "stairs": edge.get("stairs", False),
            "density": edge.get("density", 0.0),
            "green_factor": edge.get("green_factor", 1.0),
        }
        for node_edges in routing_service.adj.values()
        for edge in node_edges
    ]

    return {"nodes": list(routing_service.nodes.values()), "edges": edges}


@router.post(
    "/simulate",
    summary="Ingest Telemetry Stream",
    description=(
        "Ingests real-time hardware telemetry events to update dynamic edge crowd density weights. "
        "Each event specifies a source node, target node, and new density value (0.0–1.0)."
    ),
    response_description="Count of ingested events and successfully updated edges.",
)
def ingest_telemetry(stream: TelemetryStream) -> dict:
    """
    Processes a batch of telemetry density update events.

    Args:
        stream: TelemetryStream containing one or more TelemetryEvent records.

    Returns:
        Dict with ingested event count and successfully updated edge count.
    """
    updated_count = 0
    for event in stream.events:
        success = routing_service.update_edge_density(
            source=event.source, target=event.target, density=event.density
        )
        if success:
            updated_count += 1

    logger.info(
        "Telemetry stream ingested.",
        extra={
            "ingested_events": len(stream.events),
            "updated_edges": updated_count,
        },
    )

    return {
        "status": "success",
        "ingested_events": len(stream.events),
        "updated_edges": updated_count,
    }
