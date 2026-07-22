from pathlib import Path

import pytest

from developer_setup import PROJECT_TEMPLATE_ITEMS
from developer_setup_gui import (
    DeveloperSetupFormData,
    build_setup_request,
    create_review_lines,
    create_step_states,
)


def test_console_form_builds_setup_request(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "CustomerPortal"
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=f"  {destination}  ",
            application_name="  Customer Portal  ",
            email_mode="console",
            database_provider="sqlite",
        )
    )

    assert request.destination == destination.resolve()
    assert request.application_name == "Customer Portal"
    assert request.email_mode == "console"
    assert request.database_provider == "sqlite"
    assert request.database_url is None


@pytest.mark.parametrize(
    (
        "page_index",
        "expected_states",
    ),
    [
        (
            0,
            (
                "current",
                "pending",
                "pending",
                "pending",
                "pending",
            ),
        ),
        (
            1,
            (
                "completed",
                "current",
                "pending",
                "pending",
                "pending",
            ),
        ),
        (
            2,
            (
                "completed",
                "completed",
                "current",
                "pending",
                "pending",
            ),
        ),
        (
            3,
            (
                "completed",
                "completed",
                "completed",
                "current",
                "pending",
            ),
        ),
        (
            4,
            (
                "completed",
                "completed",
                "completed",
                "completed",
                "current",
            ),
        ),
    ],
)
def test_wizard_step_states_follow_current_page(
    page_index: int,
    expected_states: tuple[str, ...],
) -> None:
    assert create_step_states(
        page_index
    ) == expected_states


def test_hidden_email_fields_are_ignored_when_mode_changes(
    tmp_path: Path,
) -> None:
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=str(tmp_path / "ConsoleApplication"),
            application_name="Console Application",
            email_mode="console",
            gmail_address="old@gmail.com",
            gmail_app_password="old-password",
            smtp_host="old.smtp.test",
            smtp_port="465",
            smtp_security="ssl",
            smtp_sender_email="old@example.test",
            database_provider="sqlite",
        )
    )

    assert request.gmail_address is None
    assert request.gmail_app_password is None
    assert request.smtp_host is None
    assert request.smtp_port is None


def test_public_access_url_is_included_in_request(
    tmp_path: Path,
) -> None:
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=str(tmp_path / "TunnelApplication"),
            application_name="Tunnel Application",
            email_mode="console",
            access_mode="public",
            public_base_url=(
                "https://sample.trycloudflare.com/"
            ),
            database_provider="sqlite",
        )
    )

    assert request.public_base_url == (
        "https://sample.trycloudflare.com"
    )


def test_gmail_app_password_spaces_are_removed_from_form(
    tmp_path: Path,
) -> None:
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=str(tmp_path / "GmailApplication"),
            application_name="Gmail Application",
            email_mode="gmail",
            gmail_address="developer@gmail.com",
            gmail_app_password="abcd efgh ijkl mnop",
            database_provider="sqlite",
        )
    )

    assert request.gmail_app_password is not None
    assert (
        request.gmail_app_password.get_secret_value()
        == "abcdefghijklmnop"
    )


def test_custom_smtp_and_database_form_is_supported(
    tmp_path: Path,
) -> None:
    database_url = (
        "postgresql+psycopg://customer:secret@"
        "db.example.test:5432/customer"
    )
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=str(tmp_path / "CustomerApplication"),
            application_name="Customer Application",
            email_mode="smtp",
            smtp_host="smtp.example.test",
            smtp_port="465",
            smtp_security="ssl",
            smtp_username="smtp-user",
            smtp_password="smtp-secret",
            smtp_sender_email="sender@example.test",
            smtp_sender_name="Customer Mail",
            database_provider="postgresql",
            database_url=database_url,
        )
    )

    assert request.smtp_port == 465
    assert request.smtp_security == "ssl"
    assert request.smtp_password is not None
    assert (
        request.smtp_password.get_secret_value()
        == "smtp-secret"
    )
    assert request.database_url is not None
    assert (
        request.database_url.get_secret_value()
        == database_url
    )


def test_invalid_smtp_port_has_clear_message(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="SMTP port must be a whole number",
    ):
        build_setup_request(
            DeveloperSetupFormData(
                destination=str(tmp_path / "SMTPApplication"),
                application_name="SMTP Application",
                email_mode="smtp",
                smtp_host="smtp.example.test",
                smtp_port="not-a-number",
                smtp_security="starttls",
                smtp_sender_email="sender@example.test",
                database_provider="sqlite",
            )
        )


def test_review_does_not_expose_secrets(
    tmp_path: Path,
) -> None:
    database_secret = "database-secret"
    smtp_secret = "smtp-secret"
    request = build_setup_request(
        DeveloperSetupFormData(
            destination=str(tmp_path / "SecureApplication"),
            application_name="Secure Application",
            email_mode="smtp",
            smtp_host="smtp.example.test",
            smtp_port="587",
            smtp_security="starttls",
            smtp_username="smtp-user",
            smtp_password=smtp_secret,
            smtp_sender_email="sender@example.test",
            database_provider="postgresql",
            access_mode="public",
            public_base_url=(
                "https://secure.trycloudflare.com"
            ),
            database_url=(
                "postgresql+psycopg://customer:"
                f"{database_secret}@db.example.test/customer"
            ),
        )
    )

    review_text = "\n".join(
        create_review_lines(request)
    )

    assert smtp_secret not in review_text
    assert database_secret not in review_text
    assert "credentials provided" in review_text
    assert "connection URL provided" in review_text
    assert (
        "https://secure.trycloudflare.com"
        in review_text
    )


def test_wizard_spec_bundles_project_template() -> None:
    project_directory = (
        Path(__file__).resolve().parents[1]
    )
    spec_text = (
        project_directory
        / "DeveloperSetupWizard.spec"
    ).read_text(
        encoding="utf-8"
    )

    for item_name in PROJECT_TEMPLATE_ITEMS:
        assert f'"{item_name}"' in spec_text

    installer_text = (
        project_directory
        / "DeveloperSetupWizardInstaller.iss"
    ).read_text(
        encoding="utf-8"
    )
    assert (
        "ApplicationStarterDeveloperSetup.exe"
        in installer_text
    )
