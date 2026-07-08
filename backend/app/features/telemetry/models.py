from pydantic import BaseModel, Field
from typing import List


class TelemetryEvent(BaseModel):
    source: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Source node ID (e.g., Section_101)",
    )
    target: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Target node ID (e.g., Stairs_North)",
    )
    density: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Dynamic crowd density index (must be between 0.0 and 1.0)",
    )


class TelemetryStream(BaseModel):
    events: List[TelemetryEvent] = Field(
        ..., description="A batch list of telemetry events to ingest in real-time"
    )
