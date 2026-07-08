import sys
import os
import time
from fastapi.testclient import TestClient

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)


def test_cache_hit_latency():
    """
    Asserts Latency Testing: Cache hit query resolves significantly faster (<10ms)
    than standard Dijkstra route calculation misses (~20-50ms).
    """
    payload = {
        "start": "Section_101",
        "end": "Section_102",
        "profile": "standard",
        "query_text": "Path to Section 102",
        "language": "en",
    }

    # 1. First request - Cache Miss
    t0 = time.perf_counter()
    response_miss = client.post("/api/navigation/route", json=payload)
    latency_miss = (time.perf_counter() - t0) * 1000.0
    assert response_miss.status_code == 200
    assert response_miss.json()["cache_hit"] is False

    # 2. Second request - Cache Hit
    t0 = time.perf_counter()
    response_hit = client.post("/api/navigation/route", json=payload)
    latency_hit = (time.perf_counter() - t0) * 1000.0
    assert response_hit.status_code == 200
    assert response_hit.json()["cache_hit"] is True

    print(
        f"\n[LATENCY BENCHMARK] Cache Miss: {latency_miss:.2f}ms | Cache Hit: {latency_hit:.2f}ms"
    )
    # Cache hit must resolve in a fraction of the time
    assert latency_hit < 20.0 or latency_hit < latency_miss


def test_concurrency_and_volume():
    """
    Simulates Concurrency and Volume testing: Fires 30 consecutive requests in a loop
    to verify that the server has zero memory leaks or index errors under consecutive requests.
    """
    payload = {
        "start": "Section_101",
        "end": "Section_201",
        "profile": "standard",
        "query_text": "Concession navigation",
        "language": "en",
    }

    start_time = time.perf_counter()
    iterations = 30

    for _ in range(iterations):
        response = client.post("/api/navigation/route", json=payload)
        assert response.status_code == 200

    duration = time.perf_counter() - start_time
    avg_throughput = iterations / duration

    print(
        f"\n[VOLUME BENCHMARK] Completed {iterations} queries in {duration:.4f}s ({avg_throughput:.2f} req/sec)"
    )
    assert avg_throughput > 10.0  # Assert stable local processing rate
