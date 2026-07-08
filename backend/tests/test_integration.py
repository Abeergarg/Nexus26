import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.features.operations.weather import get_external_weather
from app.core.cache import redis_client

client = TestClient(app)


def test_api_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "OPERATIONAL"


def test_api_topology_retrieval():
    response = client.get("/api/telemetry/topology")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0


def test_api_route_calculation():
    payload = {
        "start": "Section_101",
        "end": "Section_102",
        "profile": "standard",
        "query_text": "Guide me from Section 101 to Section 102",
        "language": "en",
    }
    response = client.post("/api/navigation/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "path" in data
    assert "steps" in data


def test_api_validation_error_handling():
    """
    Verifies that type-safe validation boundary violations (density = 1.5, which violates pydantic le=1.0)
    are intercepted by the centralized handler and return a clean 422 structured error.
    """
    payload = {
        "events": [
            {
                "source": "Section_101",
                "target": "Section_102",
                "density": 1.5,  # OUT OF BOUNDS (Pydantic max limit 1.0)
            }
        ]
    }
    response = client.post("/api/telemetry/simulate", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INPUT_VALIDATION_ERROR"
    assert "details" in data["error"]
    assert any(x["field"] == "events -> 0 -> density" for x in data["error"]["details"])


@pytest.mark.anyio
async def test_async_weather_caching_and_resilience():
    """
    Tests that the async weather service successfully uses the cache if populated.
    """
    redis_client.raw_kv.clear()

    # Pre-populate cache to simulate cache hit
    redis_client.set("weather_cache", {"temp_c": 19.5, "humidity": 55.0}, ttl_secs=10)

    temp, hum = await get_external_weather()
    assert temp == 19.5
    assert hum == 55.0

    # Invalidate cache
    redis_client.raw_kv.clear()

    # Fetching weather now should trigger network search or fallback
    temp, hum = await get_external_weather()
    assert 10.0 <= temp <= 45.0
    assert 0.0 <= hum <= 100.0
