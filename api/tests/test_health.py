"""Tests cho /healthz endpoint."""
from unittest.mock import patch


def test_health_ok():
    with (
        patch("app.core.db.get_pool"),
        patch("app.core.queue.open_arq_pool"),
        patch("app.core.queue.close_arq_pool"),
        patch("app.core.db.close_pool"),
        patch("app.core.db.healthcheck", return_value=True),
    ):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            res = client.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
