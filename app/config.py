"""Application settings and configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/privio_db"
    )
    app_name: str = "Privio Commitments API"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # HTTP Basic Authentication Credentials
    editor_user: str = "editor"
    editor_pass: str = "editor123"
    viewer_user: str = "viewer"
    viewer_pass: str = "viewer123"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
