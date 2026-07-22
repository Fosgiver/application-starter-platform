import pytest
from pydantic import ValidationError

from app.core.settings import Settings


TEST_JWT_SECRET = (
    "test-only-jwt-secret-that-is-longer-than-32-characters"
)


def create_test_settings(
    public_base_url: str,
) -> Settings:
    return Settings(
        jwt_secret_key=TEST_JWT_SECRET,
        public_base_url=public_base_url,
    )


def test_public_base_url_removes_trailing_slash() -> None:
    settings = create_test_settings(
        "https://example.test/"
    )

    assert (
        settings.public_base_url
        == "https://example.test"
    )


def test_email_verification_url_uses_public_base_url() -> None:
    settings = create_test_settings(
        "https://example.test/"
    )

    assert settings.email_verification_frontend_url == (
        "https://example.test/verify-email.html"
    )


def test_password_reset_url_uses_public_base_url() -> None:
    settings = create_test_settings(
        "https://example.test/"
    )

    assert settings.password_reset_frontend_url == (
        "https://example.test/reset-password.html"
    )


def test_public_base_url_rejects_non_http_url() -> None:
    with pytest.raises(
        ValidationError,
        match="public_base_url must be a valid",
    ):
        create_test_settings(
            "ftp://example.test"
        )


def test_default_smtp_security_is_starttls() -> None:
    settings = Settings(
        jwt_secret_key=TEST_JWT_SECRET,
    )

    assert settings.smtp_security == "starttls"


@pytest.mark.parametrize(
    "smtp_security",
    [
        "starttls",
        "ssl",
        "none",
    ],
)
def test_supported_smtp_security_modes_are_accepted(
    smtp_security: str,
) -> None:
    settings = Settings(
        jwt_secret_key=TEST_JWT_SECRET,
        smtp_security=smtp_security,
    )

    assert settings.smtp_security == smtp_security


def test_unknown_smtp_security_mode_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="smtp_security",
    ):
        Settings(
            jwt_secret_key=TEST_JWT_SECRET,
            smtp_security="unknown",
        )