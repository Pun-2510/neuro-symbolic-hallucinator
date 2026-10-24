"""Unit tests cho config và bảo mật JWT_SECRET / biến môi trường."""

from __future__ import annotations

import pytest

from integrity_checker.config import AppConfig, Settings, get_settings


def test_auth_config_defaults():
    """AuthConfig should have correct default values."""
    settings = get_settings()
    assert hasattr(settings, "auth")
    assert settings.auth.jwt_secret is not None
    assert settings.auth.token_expire_hours == 24


def test_app_config_default_debug_is_false():
    """AppConfig.debug should default to False for security."""
    cfg = AppConfig()
    assert cfg.debug is False


def test_production_yaml_env_rejects_default_jwt_secret(monkeypatch):
    """When app.env='production' in YAML (even if APP_ENV env var is unset), default JWT_SECRET must fail."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValueError, match="JWT_SECRET must be set via environment variable in production"):
        Settings(app={"env": "production"})


def test_production_env_rejects_weak_jwt_secret_from_env(monkeypatch):
    """Weak JWT_SECRET (<32 chars) passed via environment variable must not bypass validation."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "too-short-secret-123")

    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings()


def test_production_env_rejects_known_placeholder_secret(monkeypatch):
    """Known placeholder secret (>32 chars) must still be rejected in production."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "citra-secret-key-change-in-production-2026")

    with pytest.raises(ValueError, match="JWT_SECRET must be set via environment variable in production"):
        Settings()


def test_production_env_accepts_strong_jwt_secret(monkeypatch):
    """Strong >=32 char random JWT_SECRET succeeds in production."""
    strong_secret = "a9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", strong_secret)

    settings = Settings()
    assert settings.app.env == "production"
    assert settings.auth.jwt_secret == strong_secret


def test_env_overrides_mapped_to_settings(monkeypatch):
    """APP_DEBUG, APP_LOG_LEVEL, and GROBID_URL env vars map into Settings."""
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("APP_LOG_LEVEL", "warning")
    monkeypatch.setenv("GROBID_URL", "http://grobid:8070")

    settings = Settings(app={"debug": True, "log_level": "INFO"})
    assert settings.app.debug is False
    assert settings.app.log_level == "WARNING"
    assert settings.extraction.grobid.url == "http://grobid:8070"
