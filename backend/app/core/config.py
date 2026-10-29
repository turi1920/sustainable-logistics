from decimal import Decimal
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "Sustainable Reverse Logistics System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./reverse_logistics.db"
    
    # Financial & NRV Defaults (Decimal values for monetary precision)
    DEFAULT_CURRENCY: str = "USD"
    AVERAGE_TRANSPORTATION_COST: Decimal = Field(default=Decimal("15.00"))
    DEFAULT_PACKAGING_COST: Decimal = Field(default=Decimal("5.00"))
    DEFAULT_SANITIZATION_COST: Decimal = Field(default=Decimal("12.00"))

    # 5-Day SLA Non-Response Workflow
    SLA_TIMEOUT_DAYS: int = 5
    REMINDER_1_HOURS: int = 48
    REMINDER_2_HOURS: int = 96
    SLA_CHECK_INTERVAL_SECONDS: int = 900

    # Storage
    UPLOAD_STORAGE_PATH: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:3000"]


settings = Settings()
