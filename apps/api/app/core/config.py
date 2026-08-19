from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Logistics Compliance Intelligence Platform API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # Development-only identity shim; see app/core/security.py. Startup fails
    # if this is left on in a production-like environment.
    auth_mode: Literal["dev_header"] = "dev_header"

    database_url: str = (
        "postgresql+psycopg://logistics:logistics@localhost:5432/logistics_compliance"
    )

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
