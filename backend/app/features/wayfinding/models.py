from pydantic import BaseModel, Field
from typing import List, Literal, Dict


class RouteRequest(BaseModel):
    start: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Starting location node ID (e.g., Section_101)",
    )
    end: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Destination location node ID (e.g., Gate_A)",
    )
    profile: Literal["standard", "mobility_impaired", "green"] = Field(
        "standard",
        description="Dijkstra weight profile: standard, mobility_impaired (stairs-free), or green (low carbon)",
    )
    query_text: str = Field(
        "", max_length=400, description="Natural language user request, scrubbed of PII"
    )
    language: Literal["en", "es", "fr", "ar"] = Field(
        "en", description="Direction translation language code"
    )


class RouteResponse(BaseModel):
    success: bool
    profile: str
    profile_label: str
    language: str
    path: List[str]
    total_distance_meters: float
    total_time_minutes: float
    estimated_carbon_grams: float
    carbon_info: str
    steps: List[str]
    scrubbed_query: str
    scrub_stats: Dict[str, int]
    cache_hit: bool
    similarity_score: float
    latency_ms: float
