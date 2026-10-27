from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "Takeaway Platform API"
    api_prefix: str = "/api/v1"
    secret_key: str = "local-only-change-this-secret-key-32-bytes"
    database_url: str = (
        "postgresql+psycopg://takeaway:takeaway_dev_password@localhost:5432/takeaway"
    )
    frontend_origin: str = "http://localhost:8080"
    redis_url: str | None = None
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    rate_limit_enabled: bool = True
    auth_rate_limit_per_minute: int = 10
    order_rate_limit_per_minute: int = 20

    @field_validator("redis_url", mode="before")
    @classmethod
    def empty_redis_url(cls, value: str | None) -> str | None:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
