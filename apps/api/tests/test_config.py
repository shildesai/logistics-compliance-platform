"""Unit tests for application configuration."""

from app.core.config import Settings, get_settings


def test_settings_have_sane_defaults():
    settings = Settings(_env_file=None)

    assert settings.api_v1_prefix == "/api/v1"
    assert settings.environment == "development"
    assert "postgresql" in settings.database_url


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
