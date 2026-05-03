"""
Application settings configuration.

Loads settings from environment variables with sensible defaults.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_SECRET = "changeme-generate-with-openssl-rand-hex-32"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./geo_chat.db"

    # JWT Authentication
    jwt_secret_key: str = _PLACEHOLDER_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours - allows long-running analysis operations

    # External services
    mistral_key: str = ""
    email: str = ""
    ncbi_api_key: str = ""

    @field_validator("jwt_secret_key")
    @classmethod
    def require_strong_secret(cls, v: str) -> str:
        if v == _PLACEHOLDER_SECRET or len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong random secret (≥32 chars). "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars


settings = Settings()
