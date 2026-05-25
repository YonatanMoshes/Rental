from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    app_name: str = "Rental Fleet Manager API"
    environment: str = "local"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "rental_fleet"
    log_level: str = "INFO"
    log_file: str = "logs/rental_fleet.log"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
