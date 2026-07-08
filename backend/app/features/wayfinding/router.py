from fastapi import APIRouter
from app.features.wayfinding.models import RouteRequest, RouteResponse
from app.features.wayfinding.service import routing_service
from app.core.security import scrub_pii
from app.core.cache import redis_client

router = APIRouter()


@router.post(
    "/route",
    response_model=RouteResponse,
    description="Calculates the optimal route while scrubbing input PII and querying the semantic cache.",
)
def find_route(req: RouteRequest):
    # 1. Privacy Scrubbing
    scrubbed_text, scrub_stats = scrub_pii(req.query_text)

    # 2. Namespace cache prefix to isolate by path and profile parameters
    cache_prefix = f"{req.start}_{req.end}_{req.profile}_{req.language}_"
    cache_key = f"{cache_prefix}{scrubbed_text}"

    # 3. Semantic Cache Query
    cached_val, is_hit, similarity, latency = redis_client.get_semantic(
        query=scrubbed_text, prefix=cache_prefix, threshold=0.82
    )

    if is_hit and cached_val:
        return RouteResponse(
            success=cached_val["success"],
            profile=cached_val["profile"],
            profile_label=cached_val["profile_label"],
            language=cached_val["language"],
            path=cached_val["path"],
            total_distance_meters=cached_val["total_distance_meters"],
            total_time_minutes=cached_val["total_time_minutes"],
            estimated_carbon_grams=cached_val["estimated_carbon_grams"],
            carbon_info=cached_val["carbon_info"],
            steps=cached_val["steps"],
            scrubbed_query=scrubbed_text,
            scrub_stats=scrub_stats,
            cache_hit=True,
            similarity_score=round(similarity, 4),
            latency_ms=round(latency, 2),
        )

    # 4. Cache Miss - Calculate Route via Dijkstra Graph Solver
    route_result = routing_service.calculate_route(
        start=req.start, end=req.end, profile=req.profile, lang=req.language
    )

    # Store calculated result in semantic cache (infinite TTL for wayfinding maps)
    redis_client.set_semantic(cache_key, route_result)

    return RouteResponse(
        success=route_result["success"],
        profile=route_result["profile"],
        profile_label=route_result["profile_label"],
        language=route_result["language"],
        path=route_result["path"],
        total_distance_meters=route_result["total_distance_meters"],
        total_time_minutes=route_result["total_time_minutes"],
        estimated_carbon_grams=route_result["estimated_carbon_grams"],
        carbon_info=route_result["carbon_info"],
        steps=route_result["steps"],
        scrubbed_query=scrubbed_text,
        scrub_stats=scrub_stats,
        cache_hit=False,
        similarity_score=round(similarity, 4),
        latency_ms=round(latency, 2),
    )
