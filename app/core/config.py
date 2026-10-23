"""Settings loaded from environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./realworld.db"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    host: str = "0.0.0.0"
    port: int = 8000
    service_name: str = "realworld-lite"
    log_level: str = "INFO"
    rate_limit: str = "60/minute"
    auth_rate_limit: str = "10/minute"
    cors_origins: str = "*"
    auto_create_tables: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
