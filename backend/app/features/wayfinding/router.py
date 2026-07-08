"""
Wayfinding API router for Project Nexus26.

Endpoints:
  - POST /api/navigation/route — Calculate optimal route with PII scrubbing and semantic cache.
"""

from fastapi import APIRouter, HTTPException

from app.core.cache import redis_client
from app.core.constants import SEMANTIC_CACHE_THRESHOLD
from app.core.logging import get_structured_logger
from app.core.security import scrub_pii
from app.features.wayfinding.models import RouteRequest, RouteResponse
from app.features.wayfinding.service import routing_service

router = APIRouter()
logger = get_structured_logger("WayfindingRouter")


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="Calculate Optimal Route",
    description=(
        "Calculates the optimal pedestrian route between two stadium locations. "
        "Scrubs PII from query text, checks the semantic cache, and falls back to "
        "Dijkstra graph solving on a cache miss. Supports three routing profiles and "
        "four languages."
    ),
    response_description="Full route plan including turn-by-turn steps, distance, time, and carbon footprint.",
)
def find_route(req: RouteRequest) -> RouteResponse:
    """
    Processes a wayfinding request.

    Steps:
      1. Validate that start and end nodes are different.
      2. Scrub PII from the natural language query text.
      3. Check the semantic cache for a similar prior query.
      4. On cache miss, solve via Dijkstra and cache the result.

    Args:
        req: Validated RouteRequest payload.

    Returns:
        RouteResponse with path, steps, metrics, and cache metadata.
    """
    # Guard: reject trivial same-node requests early
    if req.start == req.end:
        raise HTTPException(
            status_code=400,
            detail="Start and destination nodes must be different.",
        )

    # 1. PII scrubbing
    scrubbed_text, scrub_stats = scrub_pii(req.query_text)
    if any(v > 0 for v in scrub_stats.values()):
        logger.info(
            "PII scrubbed from route query.",
            extra={"scrub_stats": scrub_stats},
        )

    # 2. Semantic cache lookup
    cache_prefix = f"{req.start}_{req.end}_{req.profile}_{req.language}_"
    cache_key = f"{cache_prefix}{scrubbed_text}"

    cached_val, is_hit, similarity, latency = redis_client.get_semantic(
        query=scrubbed_text, prefix=cache_prefix, threshold=SEMANTIC_CACHE_THRESHOLD
    )

    if is_hit and cached_val:
        logger.info(
            "Semantic cache HIT for route query.",
            extra={
                "start": req.start,
                "end": req.end,
                "profile": req.profile,
                "similarity": round(similarity, 4),
                "latency_ms": round(latency, 2),
            },
        )
        return RouteResponse(
            **cached_val,
            scrubbed_query=scrubbed_text,
            scrub_stats=scrub_stats,
            cache_hit=True,
            similarity_score=round(similarity, 4),
            latency_ms=round(latency, 2),
        )

    # 3. Cache miss — solve via Dijkstra
    logger.info(
        "Semantic cache MISS — solving via Dijkstra.",
        extra={
            "start": req.start,
            "end": req.end,
            "profile": req.profile,
            "language": req.language,
            "similarity": round(similarity, 4),
        },
    )

    route_result = routing_service.calculate_route(
        start=req.start, end=req.end, profile=req.profile, lang=req.language
    )

    # Store calculated result in semantic cache (no TTL — topology is deterministic)
    redis_client.set_semantic(cache_key, route_result)

    return RouteResponse(
        **route_result,
        scrubbed_query=scrubbed_text,
        scrub_stats=scrub_stats,
        cache_hit=False,
        similarity_score=round(similarity, 4),
        latency_ms=round(latency, 2),
    )
