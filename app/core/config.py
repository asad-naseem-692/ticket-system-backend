import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/customer_support"
    )
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "super-secret-default-key-change-in-production-12345"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # Fixed SLA rules (in hours) as specified in hard rules
    SLA_HOURS: dict = {
        "critical": 2,
        "high": 8,
        "medium": 24,
        "low": 72,
    }

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["http://localhost:3000"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
