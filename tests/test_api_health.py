"""API smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ma_darwin.api import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
