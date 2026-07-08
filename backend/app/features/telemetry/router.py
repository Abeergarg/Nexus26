from fastapi import APIRouter
from app.features.telemetry.models import TelemetryStream
from app.features.wayfinding.service import routing_service

router = APIRouter()


@router.get(
    "/topology",
    description="Exposes the static topology nodes and dynamic bidirectional crowd density graph.",
)
def get_topology():
    return {
        "nodes": list(routing_service.nodes.values()),
        "edges": [
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
        ],
    }


@router.post(
    "/simulate",
    description="Ingests real-time hardware telemetry streams to adjust dynamic edge congestion weights.",
)
def ingest_telemetry(stream: TelemetryStream):
    updated_count = 0
    for event in stream.events:
        success = routing_service.update_edge_density(
            source=event.source, target=event.target, density=event.density
        )
        if success:
            updated_count += 1

    return {
        "status": "success",
        "ingested_events": len(stream.events),
        "updated_edges": updated_count,
    }
