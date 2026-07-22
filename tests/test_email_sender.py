from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services import email_sender


def configure_test_settings(
    monkeypatch: pytest.MonkeyPatch,
    smtp_security: str,
    smtp_port: int,
) -> None:
    test_settings = SimpleNamespace(
        smtp_enabled=True,
        environment="test",
        smtp_host="smtp.example.test",
        smtp_port=smtp_port,
        smtp_username=None,
        smtp_password=None,
        smtp_sender_email="sender@example.test",
        smtp_sender_name="Test Application",
        smtp_security=smtp_security,
    )

    monkeypatch.setattr(
        email_sender,
        "settings",
        test_settings,
    )


def create_smtp_mocks(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    MagicMock,
    MagicMock,
    MagicMock,
    MagicMock,
]:
    smtp_factory = MagicMock()
    smtp_server = (
        smtp_factory
        .return_value
        .__enter__
        .return_value
    )

    smtp_ssl_factory = MagicMock()
    smtp_ssl_server = (
        smtp_ssl_factory
        .return_value
        .__enter__
        .return_value
    )

    monkeypatch.setattr(
        email_sender.smtplib,
        "SMTP",
        smtp_factory,
    )
    monkeypatch.setattr(
        email_sender.smtplib,
        "SMTP_SSL",
        smtp_ssl_factory,
    )

    return (
        smtp_factory,
        smtp_server,
        smtp_ssl_factory,
        smtp_ssl_server,
    )


def send_test_email() -> None:
    email_sender.send_email(
        recipient_email="recipient@example.test",
        subject="SMTP test",
        text_content="Test message",
    )


def test_starttls_uses_plain_smtp_then_upgrades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_settings(
        monkeypatch,
        smtp_security="starttls",
        smtp_port=587,
    )
    (
        smtp_factory,
        smtp_server,
        smtp_ssl_factory,
        _,
    ) = create_smtp_mocks(
        monkeypatch
    )

    send_test_email()

    smtp_factory.assert_called_once_with(
        "smtp.example.test",
        587,
        timeout=15,
    )
    smtp_ssl_factory.assert_not_called()
    smtp_server.starttls.assert_called_once()
    smtp_server.send_message.assert_called_once()


def test_ssl_uses_smtp_ssl_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_settings(
        monkeypatch,
        smtp_security="ssl",
        smtp_port=465,
    )
    (
        smtp_factory,
        _,
        smtp_ssl_factory,
        smtp_ssl_server,
    ) = create_smtp_mocks(
        monkeypatch
    )

    send_test_email()

    smtp_factory.assert_not_called()
    smtp_ssl_factory.assert_called_once()
    smtp_ssl_server.starttls.assert_not_called()
    smtp_ssl_server.send_message.assert_called_once()


def test_none_uses_unencrypted_smtp_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_test_settings(
        monkeypatch,
        smtp_security="none",
        smtp_port=25,
    )
    (
        smtp_factory,
        smtp_server,
        smtp_ssl_factory,
        _,
    ) = create_smtp_mocks(
        monkeypatch
    )

    send_test_email()

    smtp_factory.assert_called_once_with(
        "smtp.example.test",
        25,
        timeout=15,
    )
    smtp_ssl_factory.assert_not_called()
    smtp_server.starttls.assert_not_called()
    smtp_server.send_message.assert_called_once()