"""Integration tests cho FastAPI."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint() -> None:
    from integrity_checker.api.main import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "disclaimer" in data
    assert "version" in data


def test_root_404() -> None:
    """Path không tồn tại → 404."""
    from integrity_checker.api.main import app

    client = TestClient(app)
    resp = client.get("/api/nonexistent")
    assert resp.status_code == 404


def test_get_essay_404() -> None:
    """Essay không tồn tại → 404."""
    from integrity_checker.api.main import app

    client = TestClient(app)
    resp = client.get("/api/essays/99999")
    assert resp.status_code == 404


def test_upload_rejects_non_pdf() -> None:
    """Upload file không phải PDF → 400."""
    from integrity_checker.api.main import app

    client = TestClient(app)
    from io import BytesIO

    resp = client.post(
        "/api/essays",
        files={"file": ("test.txt", BytesIO(b"not a pdf"), "text/plain")},
    )
    assert resp.status_code == 400