"""
Resilient external weather client for Project Nexus26.

Fetches current weather conditions for MetLife Stadium from the Open-Meteo API.
Implements:
  - In-memory TTL caching to prevent API flooding.
  - Exponential backoff retry with configurable attempts.
  - Graceful fallback to simulated summer weather on total failure.
"""

import asyncio
import random
from typing import Tuple

import httpx

from app.core.cache import redis_client
from app.core.config import settings
from app.core.constants import (
    BACKOFF_BASE_SECONDS,
    FALLBACK_HUMIDITY_MAX,
    FALLBACK_HUMIDITY_MIN,
    FALLBACK_TEMP_MAX,
    FALLBACK_TEMP_MIN,
)
from app.core.logging import get_structured_logger

logger = get_structured_logger("WeatherClient")

_WEATHER_CACHE_KEY: str = "weather_cache"


async def get_external_weather() -> Tuple[float, float]:
    """
    Fetches current temperature and humidity for MetLife Stadium.

    Strategy:
      1. Check in-memory cache (TTL = ``settings.WEATHER_CACHE_TTL`` seconds).
      2. On cache miss, call Open-Meteo API with exponential backoff retries.
      3. On total failure, return realistic summer fallback values.

    Returns:
        Tuple of (temperature_celsius, relative_humidity_percent).
    """
    cached_data = redis_client.get(_WEATHER_CACHE_KEY)
    if cached_data is not None:
        logger.info(
            "Cache HIT: weather data retrieved from cache.",
            extra={
                "temperature": cached_data.get("temp_c"),
                "humidity": cached_data.get("humidity"),
                "cache_key": _WEATHER_CACHE_KEY,
            },
        )
        return cached_data["temp_c"], cached_data["humidity"]

    logger.info("Cache MISS: fetching weather from external API.")

    url = (
        f"{settings.WEATHER_API_URL}"
        f"?latitude={settings.WEATHER_LATITUDE}"
        f"&longitude={settings.WEATHER_LONGITUDE}"
        f"&current=temperature_2m,relative_humidity_2m"
    )

    async with httpx.AsyncClient() as client:
        for attempt in range(1, settings.WEATHER_MAX_RETRIES + 1):
            sleep_time = BACKOFF_BASE_SECONDS * (2**attempt)
            try:
                logger.info(
                    f"Weather API request attempt {attempt}/{settings.WEATHER_MAX_RETRIES}.",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "timeout": settings.WEATHER_TIMEOUT,
                    },
                )
                response = await client.get(url, timeout=settings.WEATHER_TIMEOUT)

                if response.status_code == 200:
                    data = response.json()
                    temp_c = float(data["current"]["temperature_2m"])
                    humidity = float(data["current"]["relative_humidity_2m"])

                    redis_client.set(
                        _WEATHER_CACHE_KEY,
                        {"temp_c": temp_c, "humidity": humidity},
                        ttl_secs=settings.WEATHER_CACHE_TTL,
                    )
                    logger.info(
                        "Weather fetched and cached successfully.",
                        extra={
                            "temperature": temp_c,
                            "humidity": humidity,
                            "attempt": attempt,
                        },
                    )
                    return temp_c, humidity

                logger.warning(
                    f"Weather API non-200 response on attempt {attempt}.",
                    extra={"status_code": response.status_code, "attempt": attempt},
                )

            except (httpx.RequestError, httpx.TimeoutException) as err:
                logger.warning(
                    f"Weather API request error on attempt {attempt}: {type(err).__name__}.",
                    extra={
                        "exception_type": type(err).__name__,
                        "attempt": attempt,
                        "backoff_seconds": sleep_time,
                    },
                )

            if attempt < settings.WEATHER_MAX_RETRIES:
                await asyncio.sleep(sleep_time)

    # All retries exhausted — activate fallback
    fallback_temp = round(random.uniform(FALLBACK_TEMP_MIN, FALLBACK_TEMP_MAX), 1)
    fallback_humidity = round(
        random.uniform(FALLBACK_HUMIDITY_MIN, FALLBACK_HUMIDITY_MAX), 1
    )

    logger.error(
        "All weather API retries exhausted. Using fallback climate simulator.",
        extra={
            "latitude": settings.WEATHER_LATITUDE,
            "longitude": settings.WEATHER_LONGITUDE,
            "fallback_temp": fallback_temp,
            "fallback_humidity": fallback_humidity,
        },
    )
    return fallback_temp, fallback_humidity
