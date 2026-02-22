from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Ops Pulse API", description="API display name")
    app_env: str = Field(default="local", description="Application environment")
    debug: bool = Field(default=False, description="Enable debug behavior")
    api_version: str = Field(default="0.1.0", description="API version")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ops_pulse.db",
        description="Async SQLAlchemy database URL",
    )
    api_token: str | None = Field(
        default=None,
        description="Optional bearer token for protected routes",
    )
    jwt_access_secret: str = Field(
        default="dev-access-secret-change-me-32-bytes",
        description="JWT secret for access tokens (override in production).",
    )
    jwt_refresh_secret: str = Field(
        default="dev-refresh-secret-change-me-32-bytes",
        description="JWT secret for refresh tokens (override in production).",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_ttl_minutes: int = Field(default=15, ge=1, description="Access token TTL in minutes")
    jwt_refresh_ttl_days: int = Field(default=7, ge=1, description="Refresh token TTL in days")
    rate_limit_enabled: bool = Field(
        default=False,
        description="Enable Redis/Valkey-backed rate limiting",
    )
    rate_limit_redis_url: str | None = Field(
        default=None,
        description="Redis/Valkey URL used for rate limiting backend",
    )
    rate_limit_per_minute: int = Field(default=30, ge=1, description="Per-minute request limit")
    rate_limit_per_second: int = Field(default=5, ge=1, description="Per-second burst limit")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
