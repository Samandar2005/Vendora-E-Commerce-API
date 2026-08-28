from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core settings
    CORS_ORIGINS: str = "*"
    SECRET_KEY: str = "default_secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database Settings (.env fayldagi nomlarga moslandi)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_ADDRESS: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "vendora_db"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/vendora_db"

    # Redis & Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Metadata variables
    title: str = "Vendora E-Commerce API"
    description: str = "Multi-vendor e-commerce backend API"
    version: str = "v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_ADDRESS}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()