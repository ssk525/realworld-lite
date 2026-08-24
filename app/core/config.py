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


@lru_cache
def get_settings() -> Settings:
    return Settings()
