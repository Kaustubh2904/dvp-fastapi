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
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.POSTGRES_PASSWORD)
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{encoded_password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

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
    EMAIL_PROVIDER: str = "smtp"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = False
    SMTP_USE_SSL: bool = False
    EMAIL_QUEUE_RETRY_LIMIT: int = 3

    # Subscription defaults
    DEFAULT_TRIAL_DAYS: int = 14
    DEFAULT_BILLING_CYCLE_DAYS: int = 30
    DEFAULT_EXPIRY_REMINDER_DAYS: int = 7
    MONTHLY_QUOTA_RESET_DAY: int = 1

    # Initial superadmin bootstrap credentials
    SUPERADMIN_EMAIL: Optional[str] = None
    SUPERADMIN_PASSWORD: Optional[str] = None

    # DigiLocker OAuth 2.0 Integration
    DIGILOCKER_CLIENT_ID: Optional[str] = None
    DIGILOCKER_CLIENT_SECRET: Optional[str] = None
    DIGILOCKER_REDIRECT_URI: str = "http://localhost:8000/api/v1/digilocker/callback"
    DIGILOCKER_AUTH_URL: str = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/authorize"
    DIGILOCKER_TOKEN_URL: str = "https://digilocker.meripehchaan.gov.in/public/oauth2/1/token"
    DIGILOCKER_API_BASE_URL: str = "https://digilocker.meripehchaan.gov.in/public/oauth2/1"
    DIGILOCKER_SCOPES: str = "openid"

    # Encryption key for sensitive data (DigiLocker tokens, etc.)
    FERNET_ENCRYPTION_KEY: Optional[str] = None

    @property
    def digilocker_configured(self) -> bool:
        """Returns True when DigiLocker integration has valid credentials configured."""
        return bool(self.DIGILOCKER_CLIENT_ID and self.DIGILOCKER_CLIENT_SECRET)


settings = Settings()
