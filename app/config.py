"""Application configuration with canonical Admin/Client credentials."""

from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/privio_db"
    )
    app_name: str = "Privio Commitments API"
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    preview_mode: bool = False
    demo_mode: bool = False

    admin_user: str = "admin"
    admin_pass: str = "admin123"
    client_user: str = "client"
    client_pass: str = "client123"
    session_secret: str = "change-me-in-production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Self:
        names = [self.admin_user, self.client_user]
        if (
            any(not name.strip() or ":" in name for name in names)
            or names[0] == names[1]
        ):
            raise ValueError(
                "Admin and Client require distinct, nonempty login names without colons"
            )
        if not self.admin_pass or not self.client_pass or not self.session_secret:
            raise ValueError("Authentication secrets must not be empty")
        if self.environment == "production":
            if not self.demo_mode and "test" in (self.admin_pass, self.client_pass):
                raise ValueError("Public test passwords require demo mode")
            required = {"admin_pass", "client_pass", "session_secret"}
            if (
                not required <= self.model_fields_set
                or self.admin_pass == "admin123"
                or self.client_pass == "client123"
                or self.session_secret == "change-me-in-production"
            ):
                raise ValueError(
                    "Production requires explicit Admin/Client passwords and session secret"
                )
        return self


settings = Settings()
