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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
