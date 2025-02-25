import os
from dotenv import load_dotenv
from typing import List, Any
from pydantic import BaseModel, validator, Field

# Load environment variables from .env file
load_dotenv()

class Settings(BaseModel):
    """Application-wide configuration settings loaded from environment variables or defaults."""
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://admin:password@localhost/network_db",
        env="DATABASE_URL",
        description="SQLAlchemy database connection URL"
    )

    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL for caching"
    )

    # Celery settings
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL",
        description="Celery broker URL (e.g., Redis or RabbitMQ)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND",
        description="Celery result backend URL"
    )

    # Security settings
    SECRET_KEY: str = Field(
        default="your-secret-key",
        env="SECRET_KEY",
        description="Secret key for JWT token encryption"
    )
    ALGORITHM: str = Field(
        default="HS256",
        env="ALGORITHM",
        description="JWT encryption algorithm (e.g., HS256, HS512)"
    )

    # CORS settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        env="ALLOWED_ORIGINS",
        description="Comma-separated list of allowed CORS origins"
    )

    # External service credentials
    GOOGLE_SHEETS_CREDENTIALS: str = Field(
        default="/path/to/credentials.json",
        env="GOOGLE_SHEETS_CREDENTIALS",
        description="Path to Google Sheets service account credentials JSON"
    )
    AIRTABLE_API_KEY: str = Field(
        default="your-airtable-key",
        env="AIRTABLE_API_KEY",
        description="Airtable API key"
    )
    OPENAI_API_KEY: str = Field(
        default="your-openai-key",
        env="OPENAI_API_KEY",
        description="OpenAI API key for AI insights"
    )

    # Environment settings
    ENVIRONMENT: str = Field(
        default="prod",
        env="ENVIRONMENT",
        description="Application environment (e.g., 'dev', 'prod', 'test')"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (e.g., 'DEBUG', 'INFO', 'ERROR')"
    )
    LOG_JSON: bool = Field(
        default=False,
        env="LOG_JSON",
        description="Whether to use JSON-structured logging"
    )

    # Validate ALLOWED_ORIGINS
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError("ALLOWED_ORIGINS must be a comma-separated string or list")

    # Validate ENVIRONMENT
    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        valid_environments = {"dev", "development", "prod", "production", "test"}
        return v.lower() if v.lower() in valid_environments else "prod"

    # Validate LOG_LEVEL
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        return v.upper() if v.upper() in valid_levels else "INFO"

    # Validate file paths (no logger usage here)
    @validator("GOOGLE_SHEETS_CREDENTIALS")
    def validate_credentials_path(cls, v: str) -> str:
        if not os.path.isfile(v) and "GOOGLE_SHEETS_CREDENTIALS" not in os.environ:
            print(f"Warning: Google Sheets credentials file not found at {v}", file=sys.stderr)
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

def load_settings() -> 'Settings':
    """Load settings from environment variables with validation, respecting defaults."""
    env_settings = {
        key: value for key, value in (
            (k, os.getenv(k)) for k in Settings.__fields__.keys()
        ) if value is not None  # Only include non-None values
    }
    return Settings(**env_settings)

# Initialize the settings object here to make it available for import
settings = load_settings()

if __name__ == "__main__":
    print("Settings:", settings.dict())
