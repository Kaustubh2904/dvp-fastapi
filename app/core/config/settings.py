import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    PROJECT_NAME: str = "Digital Verification Portal (DVP) API"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-at-least-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dvp"
    DATABASE_URL: Optional[str] = None

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "dvp"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    UPLOAD_DIR: str = "uploads"

    # OTP and Token limits
    OTP_EXPIRE_MINUTES: int = 5
    OTP_ATTEMPT_LIMIT: int = 3
    RESET_TOKEN_EXPIRE_MINUTES: int = 15

    # Mock Email Configuration
    MAIL_FROM: str = "noreply@dvp-portal.com"
    MAIL_SENDER: str = "DVP System"


settings = Settings()
