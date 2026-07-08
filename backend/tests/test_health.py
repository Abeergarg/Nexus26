"""
Tests for /health/live and /health/ready endpoints.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestLivenessProbe:
    def test_liveness_returns_200(self):
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_liveness_returns_alive_status(self):
        data = client.get("/health/live").json()
        assert data["status"] == "alive"

    def test_liveness_includes_version(self):
        data = client.get("/health/live").json()
        assert "version" in data
        assert isinstance(data["version"], str)


class TestReadinessProbe:
    def test_readiness_returns_200_or_503(self):
        response = client.get("/health/ready")
        assert response.status_code in (200, 503)

    def test_readiness_includes_components(self):
        data = client.get("/health/ready").json()
        assert "components" in data
        assert "topology" in data["components"]
        assert "cache" in data["components"]
        assert "config" in data["components"]

    def test_readiness_topology_ok_when_loaded(self):
        """Topology should be loaded at startup — readiness must report 'ok'."""
        data = client.get("/health/ready").json()
        assert data["components"]["topology"] == "ok"

    def test_readiness_includes_version(self):
        data = client.get("/health/ready").json()
        assert "version" in data

    def test_readiness_includes_status_field(self):
        data = client.get("/health/ready").json()
        assert data["status"] in ("ready", "degraded")
