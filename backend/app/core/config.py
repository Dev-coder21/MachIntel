from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "MachIntel"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security & Auth
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours for dev

    # Database
    DATABASE_URL: str = "postgresql://devtrivedi@localhost:5432/machintel"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # AI Inspector
    AI_INSPECTOR_PROVIDER: str = "mock"
    AI_INSPECTOR_API_KEY: Optional[str] = None
    AI_INSPECTOR_MODEL: str = "gpt-4o"
    AI_INSPECTOR_BASE_URL: Optional[str] = None
    AI_INSPECTOR_MAX_TOOL_CALLS: int = 5
    AI_INSPECTOR_TIMEOUT_SECONDS: int = 30

    # Worker & Background Infrastructure (M12)
    WORKER_ENABLED: bool = True
    SCHEDULER_ENABLED: bool = True
    WORKER_POLL_INTERVAL_SECONDS: float = 2.0
    WORKER_HEARTBEAT_INTERVAL_SECONDS: float = 5.0
    WORKER_STALE_JOB_TIMEOUT_SECONDS: float = 60.0
    WORKER_MAX_RETRIES: int = 3
    WORKER_RETRY_BACKOFF_SECONDS: float = 5.0

    # Scheduled Job Intervals (Minutes)
    EVIDENCE_REFRESH_INTERVAL_MINUTES: int = 60
    RISK_REFRESH_INTERVAL_MINUTES: int = 30
    MAINTENANCE_REFRESH_INTERVAL_MINUTES: int = 60
    ANALYTICS_REFRESH_INTERVAL_MINUTES: int = 120

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if self.SECRET_KEY == "insecure-dev-secret-key-change-in-production-min-32-chars-long" or len(self.SECRET_KEY) < 32:
                raise ValueError("In production, SECRET_KEY must be an environment-configured secret of at least 32 characters.")
            if self.DEBUG:
                raise ValueError("In production, DEBUG must be set to False.")
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("In production, wildcard CORS origin ('*') is forbidden when credentials are enabled.")
        return self


settings = Settings()
