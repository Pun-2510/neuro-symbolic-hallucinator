"""Unit tests cho config."""

from __future__ import annotations

from integrity_checker.config import get_settings


def test_auth_config_defaults():
    """AuthConfig should have correct default values."""
    settings = get_settings()
    assert hasattr(settings, 'auth')
    assert settings.auth.jwt_secret is not None
    assert settings.auth.token_expire_hours == 24
