"""
Application configuration.

All settings are loaded from environment variables (see .env.example).
Using pydantic-settings means config is validated at startup — if a
required value is missing or malformed, the app fails fast instead of
breaking later at request time.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ──
    APP_NAME: str = "GridSuite"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str
    API_V1_PREFIX: str = "/v1"

    # ── Database ──
    DATABASE_URL: str

    # ── Auth ──
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── Billing ──
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── CORS ──
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ── Ingestion adapter keys ──
    AIS_API_KEY: str = ""
    CUSTOMS_DATA_API_KEY: str = ""
    WEATHER_API_KEY: str = ""
    MACRO_DATA_API_KEY: str = ""

    # ── Object storage ──
    S3_BUCKET: str = "gridsuite-raw-data"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — avoids re-reading/validating env on every call."""
    return Settings()


settings = get_settings()
