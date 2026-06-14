from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://inkisle:changeme@localhost:5432/inkisle"
    redis_url: str = "redis://localhost:6379"

    jwt_secret: str = "dev-secret-change-in-production"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:3000"

    books_storage_path: str = "/data/books"
    covers_storage_path: str = "/data/covers"
    thumbnails_storage_path: str = "/data/thumbnails"

    scan_interval_seconds: int = 300
    max_import_workers: int = 4

    # Metadata enrichment
    google_books_api_key: str = ""
    comicvine_api_key: str = ""
    enrichment_cache_ttl_hours: int = 168
    enrichment_rate_limit_google: int = 100
    enrichment_rate_limit_comicvine: int = 200

    # OPDS
    opds_page_size: int = 50
    opds_title: str = "InkIsle Library"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
