from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import (
    Field,
    SecretStr,
    field_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from app.core.paths import (
    get_default_database_url,
    get_environment_file_path,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    # Application identity
    app_name: str = "Application Starter Platform"
    app_version: str = "0.1.0"
    environment: Literal[
        "development",
        "test",
        "production",
    ] = "development"
    debug: bool = False
    docs_enabled: bool = True

    # API server
    api_host: str = "127.0.0.1"
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
    )
    open_browser_on_start: bool = True

    # Database
    database_url: str = Field(
        default_factory=get_default_database_url
    )
    database_echo: bool = False

    # JWT authentication
    jwt_secret_key: SecretStr = Field(
        min_length=32
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = Field(
        default=30,
        ge=1,
    )
    jwt_issuer: str = (
        "application-starter-platform"
    )
    jwt_audience: str = (
        "application-starter-platform-api"
    )

    # Account policies
    self_registration_enabled: bool = True
    password_min_length: int = Field(
        default=8,
        ge=8,
    )
    password_max_length: int = Field(
        default=128,
        ge=8,
    )

    # Security-token lifetimes
    email_verification_token_minutes: int = Field(
        default=1440,
        ge=1,
    )
    password_reset_token_minutes: int = Field(
        default=30,
        ge=1,
    )

    # Public address used in links sent by email
    public_base_url: str = (
        "http://127.0.0.1:8000"
    )

    @field_validator("public_base_url")
    @classmethod
    def validate_public_base_url(
        cls,
        value: str,
    ) -> str:
        normalized_value = (
            value.strip().rstrip("/")
        )
        parsed_url = urlparse(
            normalized_value
        )

        if (
            parsed_url.scheme
            not in {
                "http",
                "https",
            }
            or not parsed_url.netloc
        ):
            raise ValueError(
                "public_base_url must be a valid "
                "http:// or https:// address"
            )

        return normalized_value

    @property
    def email_verification_frontend_url(
        self,
    ) -> str:
        return (
            f"{self.public_base_url}"
            "/verify-email.html"
        )

    @property
    def password_reset_frontend_url(
        self,
    ) -> str:
        return (
            f"{self.public_base_url}"
            "/reset-password.html"
        )

    # SMTP
    smtp_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
    )
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_sender_email: str | None = None
    smtp_sender_name: str = (
        "Application Starter Platform"
    )
    smtp_security: Literal[
        "starttls",
        "ssl",
        "none",
    ] = "starttls"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        _env_file=get_environment_file_path()
    )


settings = get_settings()