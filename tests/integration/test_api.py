"""Integration tests cho FastAPI."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from integrity_checker.db.models import User, Session as SessionModel
from integrity_checker.db.session import get_session


@pytest.fixture(autouse=True)
def clean_db():
    """Clean database before each test."""
    session = get_session()
    session.query(SessionModel).delete()
    session.query(User).delete()
    session.commit()
    session.close()


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
    """Essay không tồn tại → 404 (requires auth)."""
    from integrity_checker.api.main import app

    client = TestClient(app)
    # Login first
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["token"]

    # Now try to get non-existent essay
    resp = client.get("/api/essays/99999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_upload_rejects_non_pdf() -> None:
    """Upload file không phải PDF → 400 (requires auth)."""
    from integrity_checker.api.main import app
    from io import BytesIO

    client = TestClient(app)
    # Login first
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["token"]

    resp = client.post(
        "/api/essays",
        files={"file": ("test.txt", BytesIO(b"not a pdf"), "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400