from pydantic import BaseModel, Field


class Settings(BaseModel):
    # API & Port settings
    HOST: str = Field("127.0.0.1", description="FastAPI host binding")
    PORT: int = Field(8000, description="FastAPI port binding")

    # MetLife Stadium Coordinates (FIFA World Cup 2026 venue)
    WEATHER_LATITUDE: float = Field(40.8135)
    WEATHER_LONGITUDE: float = Field(-74.0744)

    # Weather API settings
    WEATHER_API_URL: str = Field("https://api.open-meteo.com/v1/forecast")
    WEATHER_CACHE_TTL: int = Field(60, description="Weather cache lifetime in seconds")
    WEATHER_TIMEOUT: float = Field(
        2.0, description="HTTP connection timeout in seconds"
    )
    WEATHER_MAX_RETRIES: int = Field(
        3, description="Max retries for external weather fetching"
    )

    # Telemetry simulation settings
    TELEMETRY_SIM_INTERVAL: int = Field(
        5, description="Interval in seconds to update crowd densities"
    )

    # Security PII settings
    PII_MASK_STRING: str = Field("[REDACTED]")


# Global singleton settings
settings = Settings()
