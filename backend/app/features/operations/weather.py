import httpx
import asyncio
import random
from typing import Tuple

from app.core.config import settings
from app.core.cache import redis_client
from app.core.logging import get_structured_logger

logger = get_structured_logger("ResilientWeatherClient")


async def get_external_weather() -> Tuple[float, float]:
    """
    Asynchronously fetches current weather metrics for MetLife Stadium.
    Uses in-memory caching to enforce a 60s TTL and prevent API flooding.
    Implements 3 retries with exponential backoff, falling back to simulated telemetry on fail.
    """
    cache_key = "weather_cache"

    # 1. Cache hit lookup
    cached_data = redis_client.get(cache_key)
    if cached_data is not None:
        logger.info(
            "Cache Hit: Retrieved stadium weather from cache.",
            extra={
                "temperature": cached_data.get("temp_c"),
                "humidity": cached_data.get("humidity"),
            },
        )
        return cached_data["temp_c"], cached_data["humidity"]

    # 2. Cache miss - Fetch from external Open-Meteo API
    url = (
        f"{settings.WEATHER_API_URL}?latitude={settings.WEATHER_LATITUDE}"
        f"&longitude={settings.WEATHER_LONGITUDE}&current=temperature_2m,relative_humidity_2m"
    )

    async with httpx.AsyncClient() as client:
        for attempt in range(1, settings.WEATHER_MAX_RETRIES + 1):
            try:
                logger.info(
                    f"Initiating async weather API request (Attempt {attempt}/{settings.WEATHER_MAX_RETRIES})",
                    extra={"url": url},
                )

                response = await client.get(url, timeout=settings.WEATHER_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    temp_c = float(data["current"]["temperature_2m"])
                    humidity = float(data["current"]["relative_humidity_2m"])

                    # Store in cache with settings TTL
                    redis_client.set(
                        cache_key,
                        {"temp_c": temp_c, "humidity": humidity},
                        ttl_secs=settings.WEATHER_CACHE_TTL,
                    )

                    logger.info(
                        "Successfully fetched and cached external weather.",
                        extra={"temperature": temp_c, "humidity": humidity},
                    )
                    return temp_c, humidity
                else:
                    logger.warning(
                        f"Weather API returned non-200 status code: {response.status_code}",
                        extra={"status_code": response.status_code},
                    )

            except (httpx.RequestError, httpx.TimeoutException) as err:
                logger.warning(
                    f"Weather API request error on attempt {attempt}: {str(err)}",
                    extra={"exception_type": type(err).__name__, "attempt": attempt},
                )

            # Exponential backoff sleep (0.5s, 1.0s, 2.0s)
            sleep_time = 0.25 * (2**attempt)
            await asyncio.sleep(sleep_time)

    # 3. Fallback - All retries failed
    logger.error(
        "All weather API retries exhausted. Activating fallback climate simulator.",
        extra={
            "latitude": settings.WEATHER_LATITUDE,
            "longitude": settings.WEATHER_LONGITUDE,
        },
    )

    # Generate realistic summer telemetry
    fallback_temp = round(random.uniform(29.0, 34.0), 1)
    fallback_humidity = round(random.uniform(50.0, 70.0), 1)

    return fallback_temp, fallback_humidity
