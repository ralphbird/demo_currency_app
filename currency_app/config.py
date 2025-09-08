"""Configuration settings for the Currency Conversion API."""

from pathlib import Path

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration (SQLite for local/tests, PostgreSQL via env var for Docker)
    database_url: str = "sqlite:///currency_demo.db"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Dashboard Configuration
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8501

    # API Base URL for dashboard
    api_base_url: str = "http://localhost:8000"

    # Data directory for persistent storage
    data_directory: str = "data"

    # JWT Configuration
    jwt_secret_key: str = "dev-secret-key-change-in-production"

    @computed_field
    @property
    def data_dir(self) -> Path:
        """Get the data directory as a Path object."""
        # Check if we're running in Docker
        if Path("/app/data").exists():
            return Path("/app/data")
        return Path(self.data_directory)

    @field_validator("api_port", "dashboard_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port numbers are in valid range."""
        if not 1 <= v <= 65535:
            msg = "Port must be between 1 and 65535"
            raise ValueError(msg)
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            msg = "Database URL cannot be empty"
            raise ValueError(msg)
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        """Validate JWT secret key."""
        if not v:
            msg = "JWT secret key cannot be empty"
            raise ValueError(msg)
        if len(v) < 16:
            msg = "JWT secret key must be at least 16 characters long"
            raise ValueError(msg)
        return v


# Global settings instance
settings = Settings()
