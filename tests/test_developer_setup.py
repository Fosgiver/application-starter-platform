from pathlib import Path
import tomllib

import pytest
from dotenv import dotenv_values
from pydantic import ValidationError

import developer_setup
from app.core.manifest import (
    load_application_manifest,
)
from app.db.providers import (
    DatabaseProviderId,
    get_database_provider_profile,
)
from developer_setup import (
    DeveloperSetupRequest,
    configure_application_environment_example,
    configure_application_manifest,
    configure_database_dependencies,
    configure_database_environment_example,
    configure_runtime_identity,
    create_application_environment,
    create_application_installer_id,
    create_application_project,
    create_database_url_example,
    create_project_files,
    validate_destination_directory,
)


def create_setup_request(
    tmp_path: Path,
    email_mode: str,
    **email_configuration: object,
) -> DeveloperSetupRequest:
    return DeveloperSetupRequest(
        destination=(
            tmp_path
            / "TestApplication"
        ),
        application_name="Test Application",
        email_mode=email_mode,
        database_provider="sqlite",
        **email_configuration,
    )


def test_developer_setup_request(
    tmp_path: Path,
) -> None:
    destination = (
        tmp_path
        / "MyNewApplication"
    )

    request = DeveloperSetupRequest(
        destination=destination,
        application_name="My New Application",
        email_mode="console",
        database_provider="sqlite",
    )

    assert request.destination == destination
    assert request.application_name == (
        "My New Application"
    )
    assert request.email_mode == "console"
    assert request.database_provider == "sqlite"
    assert request.database_url is None


def test_bundled_setup_uses_embedded_template_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        developer_setup.sys,
        "frozen",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        developer_setup.sys,
        "_MEIPASS",
        str(tmp_path),
        raising=False,
    )

    assert (
        developer_setup.get_project_template_directory()
        == tmp_path
    )


def test_installer_id_is_stable_and_project_specific(
    tmp_path: Path,
) -> None:
    first_request = DeveloperSetupRequest(
        destination=tmp_path / "FirstLocation",
        application_name="Customer Portal",
        email_mode="console",
        database_provider="sqlite",
    )
    same_project_request = DeveloperSetupRequest(
        destination=tmp_path / "SecondLocation",
        application_name="Customer Portal",
        email_mode="console",
        database_provider="sqlite",
    )
    different_project_request = DeveloperSetupRequest(
        destination=tmp_path / "ThirdLocation",
        application_name="Inventory Portal",
        email_mode="console",
        database_provider="sqlite",
    )

    first_installer_id = (
        create_application_installer_id(
            first_request
        )
    )

    assert first_installer_id == (
        create_application_installer_id(
            same_project_request
        )
    )
    assert first_installer_id != (
        create_application_installer_id(
            different_project_request
        )
    )


def test_non_sqlite_requires_database_url(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match="Database URL is required",
    ):
        DeveloperSetupRequest(
            destination=tmp_path / "PostgreSQLApplication",
            application_name="PostgreSQL Application",
            email_mode="console",
            database_provider="postgresql",
        )


def test_matching_database_url_is_accepted(
    tmp_path: Path,
) -> None:
    database_provider = DatabaseProviderId.POSTGRESQL
    provider_profile = get_database_provider_profile(
        database_provider
    )

    request = DeveloperSetupRequest(
        destination=tmp_path / "PostgreSQLApplication",
        application_name="PostgreSQL Application",
        email_mode="console",
        database_provider=database_provider,
        database_url=provider_profile.database_url_example,
    )

    assert request.database_url is not None
    assert (
        request.database_url.get_secret_value()
        == provider_profile.database_url_example
    )


def test_mismatched_database_url_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValidationError):
        DeveloperSetupRequest(
            destination=tmp_path / "PostgreSQLApplication",
            application_name="PostgreSQL Application",
            email_mode="console",
            database_provider="postgresql",
            database_url="sqlite:///./wrong-provider.db",
        )

def test_gmail_requires_address_and_app_password(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "Gmail address and App Password "
            "are required"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="gmail",
        )


def test_complete_gmail_configuration_is_accepted(
    tmp_path: Path,
) -> None:
    request = create_setup_request(
        tmp_path,
        email_mode="gmail",
        gmail_address="developer@gmail.com",
        gmail_app_password="test-app-password",
    )

    assert request.gmail_address == (
        "developer@gmail.com"
    )
    assert request.gmail_app_password is not None
    assert (
        request.gmail_app_password.get_secret_value()
        == "test-app-password"
    )


def test_gmail_app_password_spaces_are_removed(
    tmp_path: Path,
) -> None:
    request = create_setup_request(
        tmp_path,
        email_mode="gmail",
        gmail_address="developer@gmail.com",
        gmail_app_password="abcd efgh ijkl mnop",
    )

    assert request.gmail_app_password is not None
    assert (
        request.gmail_app_password.get_secret_value()
        == "abcdefghijklmnop"
    )


@pytest.mark.parametrize(
    "public_base_url",
    (
        "example.test",
        "http://example.test",
        "https://example.test/path",
        "https://example.test?token=secret",
    ),
)
def test_invalid_public_base_url_is_rejected(
    tmp_path: Path,
    public_base_url: str,
) -> None:
    with pytest.raises(ValidationError):
        DeveloperSetupRequest(
            destination=tmp_path / "PublicApplication",
            application_name="Public Application",
            email_mode="console",
            database_provider="sqlite",
            public_base_url=public_base_url,
        )


def test_public_https_base_url_is_normalized(
    tmp_path: Path,
) -> None:
    request = DeveloperSetupRequest(
        destination=tmp_path / "PublicApplication",
        application_name="Public Application",
        email_mode="console",
        database_provider="sqlite",
        public_base_url=(
            "  https://sample.trycloudflare.com/  "
        ),
    )

    assert request.public_base_url == (
        "https://sample.trycloudflare.com"
    )


def test_gmail_rejects_custom_smtp_fields(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "Gmail mode does not accept "
            "custom SMTP fields"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="gmail",
            gmail_address="developer@gmail.com",
            gmail_app_password="test-app-password",
            smtp_host="smtp.example.test",
        )


def test_smtp_requires_connection_and_sender_fields(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "SMTP host, port, security, and "
            "sender email are required"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="smtp",
        )


def test_complete_smtp_without_authentication_is_accepted(
    tmp_path: Path,
) -> None:
    request = create_setup_request(
        tmp_path,
        email_mode="smtp",
        smtp_host="smtp.example.test",
        smtp_port=25,
        smtp_security="none",
        smtp_sender_email="sender@example.test",
        smtp_sender_name="Test Sender",
    )

    assert request.smtp_host == (
        "smtp.example.test"
    )
    assert request.smtp_port == 25
    assert request.smtp_security == "none"
    assert request.smtp_username is None
    assert request.smtp_password is None
    assert request.smtp_sender_email == (
        "sender@example.test"
    )
    assert request.smtp_sender_name == (
        "Test Sender"
    )


def test_smtp_rejects_gmail_fields(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "SMTP mode does not accept "
            "Gmail fields"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="smtp",
            smtp_host="smtp.example.test",
            smtp_port=587,
            smtp_security="starttls",
            smtp_sender_email="sender@example.test",
            gmail_address="developer@gmail.com",
        )


@pytest.mark.parametrize(
    (
        "smtp_username",
        "smtp_password",
    ),
    [
        (
            "smtp-user",
            None,
        ),
        (
            None,
            "smtp-password",
        ),
    ],
)
def test_smtp_username_and_password_must_be_together(
    tmp_path: Path,
    smtp_username: str | None,
    smtp_password: str | None,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "SMTP username and password "
            "must be provided together"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="smtp",
            smtp_host="smtp.example.test",
            smtp_port=587,
            smtp_security="starttls",
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            smtp_sender_email="sender@example.test",
        )


def test_console_rejects_email_configuration_fields(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValidationError,
        match=(
            "Console email mode does not accept "
            "email configuration fields"
        ),
    ):
        create_setup_request(
            tmp_path,
            email_mode="console",
            gmail_address="developer@gmail.com",
        )


def test_non_empty_destination_is_rejected(
    tmp_path: Path,
) -> None:
    destination = (
        tmp_path
        / "ExistingApplication"
    )
    destination.mkdir()

    existing_file = (
        destination
        / "valuable-data.txt"
    )
    existing_file.write_text(
        "This file must not be changed.",
        encoding="utf-8",
    )

    with pytest.raises(
        RuntimeError,
        match="not empty",
    ):
        validate_destination_directory(
            destination
        )

    assert existing_file.read_text(
        encoding="utf-8"
    ) == "This file must not be changed."


def test_clean_project_files_are_created(
    tmp_path: Path,
) -> None:
    source_directory = (
        Path(__file__).resolve().parents[1]
    )
    destination = (
        tmp_path
        / "GeneratedApplication"
    )

    request = DeveloperSetupRequest(
        destination=destination,
        application_name="Generated Application",
        email_mode="gmail",
        gmail_address="developer@gmail.com",
        gmail_app_password="test-app-password",
        database_provider="sqlite",
    )

    create_application_project(
        request,
        template_directory=source_directory,
    )

    manifest = load_application_manifest(
        destination
        / "application_manifest.yaml"
    )

    assert manifest.schema_version == 2

    assert manifest.application.name == (
        "Generated Application"
    )
    assert manifest.application.slug == (
        "generated-application"
    )
    assert manifest.application.version == "0.1.0"

    assert manifest.data.directory_name == (
        "GeneratedApplication"
    )

    assert manifest.database.provider == "sqlite"

    assert manifest.email.mode == "gmail"
    assert manifest.email.from_name == (
        "Generated Application"
    )

    assert manifest.packaging.executable_name == (
        "GeneratedApplication"
    )
    assert manifest.packaging.installer_name == (
        "GeneratedApplication_Setup"
    )

    assert (
        destination
        / "app"
        / "main.py"
    ).is_file()

    assert (
        destination
        / "installer.iss"
    ).is_file()

    generated_paths_text = (
        destination
        / "app"
        / "core"
        / "paths.py"
    ).read_text(
        encoding="utf-8"
    )
    assert (
        '"GeneratedApplication"'
        in generated_paths_text
    )
    assert (
        '"generated_application.db"'
        in generated_paths_text
    )
    assert (
        '"ApplicationStarterPlatform"'
        not in generated_paths_text
    )
    assert (
        '"application_starter_platform.db"'
        not in generated_paths_text
    )

    generated_spec_text = (
        destination
        / "ApplicationStarterPlatform.spec"
    ).read_text(
        encoding="utf-8"
    )
    assert generated_spec_text.count(
        'name="GeneratedApplication"'
    ) == 2
    assert (
        'name="ApplicationStarterPlatform"'
        not in generated_spec_text
    )

    generated_installer_text = (
        destination
        / "installer.iss"
    ).read_text(
        encoding="utf-8"
    )
    installer_id = create_application_installer_id(
        request
    )
    assert (
        '#define MyAppName "Generated Application"'
        in generated_installer_text
    )
    assert (
        '#define MyAppExeName '
        '"GeneratedApplication.exe"'
        in generated_installer_text
    )
    assert (
        "AppId={{" + installer_id + "}"
        in generated_installer_text
    )
    assert (
        "ApplicationStarterPlatform"
        not in generated_installer_text
    )
    assert (
        "application-starter-platform"
        not in generated_installer_text
    )
    assert (
        "APP_PUBLIC_BASE_URL="
        in generated_installer_text
    )
    assert (
        "APP_SMTP_SECURITY=starttls"
        in generated_installer_text
    )
    assert (
        "APP_EMAIL_VERIFICATION_FRONTEND_URL"
        not in generated_installer_text
    )
    assert (
        "APP_PASSWORD_RESET_FRONTEND_URL"
        not in generated_installer_text
    )
    assert (
        "APP_SMTP_USE_STARTTLS"
        not in generated_installer_text
    )

    assert (
        destination
        / "tests"
        / "test_health.py"
    ).is_file()

    generated_manifest_test_text = (
        (
            destination
            / "tests"
            / "test_manifest.py"
        ).read_text(
            encoding="utf-8"
        )
    )
    assert (
        "Application Starter Developer"
        not in generated_manifest_test_text
    )

    assert (
        destination
        / ".env"
    ).is_file()

    generated_environment_values = dotenv_values(
        destination / ".env"
    )
    assert generated_environment_values[
        "APP_DATABASE_URL"
    ] == "sqlite:///./generated_application.db"

    assert not (
        destination
        / ".venv"
    ).exists()

    assert not (
        destination
        / "developer_setup.py"
    ).exists()

    assert not (
        destination
        / "developer_setup_gui.py"
    ).exists()

    assert not (
        destination
        / "tests"
        / "test_developer_setup.py"
    ).exists()

    assert not (
        destination
        / "tests"
        / "test_developer_setup_gui.py"
    ).exists()


def read_project_dependencies(
    pyproject_path: Path,
) -> list[str]:
    with pyproject_path.open("rb") as pyproject_file:
        pyproject_data = tomllib.load(
            pyproject_file
        )

    dependencies = pyproject_data[
        "project"
    ]["dependencies"]

    assert isinstance(dependencies, list)
    assert all(
        isinstance(dependency, str)
        for dependency in dependencies
    )

    return dependencies


@pytest.mark.parametrize(
    "database_provider",
    list(DatabaseProviderId),
)
def test_selected_database_provider_dependency_is_configured(
    tmp_path: Path,
    database_provider: DatabaseProviderId,
) -> None:
    source_pyproject_path = (
        Path(__file__).resolve().parents[1]
        / "pyproject.toml"
    )
    destination = (
        tmp_path
        / database_provider.value
    )
    destination.mkdir()

    generated_pyproject_path = (
        destination
        / "pyproject.toml"
    )
    generated_pyproject_path.write_text(
        source_pyproject_path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    request = DeveloperSetupRequest(
        destination=destination,
        application_name=(
            f"{database_provider.value} Application"
        ),
        email_mode="console",
        database_provider=database_provider,
        database_url=(
            get_database_provider_profile(
                database_provider
            ).database_url_example
        ),
    )

    configure_database_dependencies(
        request
    )

    dependencies = read_project_dependencies(
        generated_pyproject_path
    )

    selected_profile = (
        get_database_provider_profile(
            database_provider
        )
    )
    selected_driver_dependency = (
        selected_profile.driver_distribution
    )

    all_driver_dependencies = {
        profile.driver_distribution
        for provider_id in DatabaseProviderId
        if (
            profile
            := get_database_provider_profile(
                provider_id
            )
        ).driver_distribution
        is not None
    }

    assert "SQLAlchemy==2.0.51" in dependencies

    if selected_driver_dependency is not None:
        assert (
            dependencies.count(
                selected_driver_dependency
            )
            == 1
        )

    unexpected_driver_dependencies = (
        all_driver_dependencies
        - {
            selected_driver_dependency
        }
    )

    assert set(dependencies).isdisjoint(
        unexpected_driver_dependencies
    )


@pytest.mark.parametrize(
    "database_provider",
    list(DatabaseProviderId),
)
def test_selected_database_provider_url_example_is_configured(
    tmp_path: Path,
    database_provider: DatabaseProviderId,
) -> None:
    source_environment_example_path = (
        Path(__file__).resolve().parents[1]
        / ".env.example"
    )
    destination = (
        tmp_path
        / database_provider.value
    )
    destination.mkdir()

    generated_environment_example_path = (
        destination
        / ".env.example"
    )
    generated_environment_example_path.write_text(
        source_environment_example_path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    request = DeveloperSetupRequest(
        destination=destination,
        application_name=(
            f"{database_provider.value} Application"
        ),
        email_mode="console",
        database_provider=database_provider,
        database_url=(
            get_database_provider_profile(
                database_provider
            ).database_url_example
        ),
    )

    configure_database_environment_example(
        request
    )

    environment_example_text = (
        generated_environment_example_path.read_text(
            encoding="utf-8"
        )
    )

    database_url_lines = [
        line
        for line
        in environment_example_text.splitlines()
        if line.startswith(
            "APP_DATABASE_URL="
        )
    ]

    assert database_url_lines == [
        (
            "APP_DATABASE_URL="
            f"{create_database_url_example(request)}"
        )
    ]
    assert (
        "# DATABASE_PROVIDER_URL_EXAMPLE"
        not in environment_example_text
    )


def test_application_environment_identity_is_configured(
    tmp_path: Path,
) -> None:
    source_environment_example_path = (
        Path(__file__).resolve().parents[1]
        / ".env.example"
    )
    destination = (
        tmp_path
        / "generated-application"
    )
    destination.mkdir()

    generated_environment_example_path = (
        destination
        / ".env.example"
    )
    generated_environment_example_path.write_text(
        source_environment_example_path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    request = DeveloperSetupRequest(
        destination=destination,
        application_name="Customer Portal",
        email_mode="console",
        database_provider="sqlite",
        public_base_url=(
            "https://customer.trycloudflare.com"
        ),
    )

    configure_application_environment_example(
        request
    )

    environment_values: dict[str, str] = {}

    for line in (
        generated_environment_example_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ):
        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        variable_name, variable_value = (
            line.split(
                "=",
                maxsplit=1,
            )
        )
        environment_values[
            variable_name
        ] = variable_value

    assert environment_values["APP_APP_NAME"] == (
        "Customer Portal"
    )
    assert environment_values["APP_APP_VERSION"] == (
        "0.1.0"
    )
    assert environment_values["APP_JWT_ISSUER"] == (
        "customer-portal"
    )
    assert environment_values["APP_JWT_AUDIENCE"] == (
        "customer-portal-api"
    )
    assert environment_values[
        "APP_SMTP_SENDER_NAME"
    ] == "Customer Portal"
    assert environment_values[
        "APP_PUBLIC_BASE_URL"
    ] == "https://customer.trycloudflare.com"


def prepare_application_environment(
    request: DeveloperSetupRequest,
) -> tuple[Path, Path]:
    source_environment_example_path = (
        Path(__file__).resolve().parents[1]
        / ".env.example"
    )
    request.destination.mkdir()

    environment_example_path = (
        request.destination
        / ".env.example"
    )
    environment_example_path.write_text(
        source_environment_example_path.read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )

    configure_database_environment_example(
        request
    )
    configure_application_environment_example(
        request
    )
    create_application_environment(
        request
    )

    return (
        request.destination / ".env",
        environment_example_path,
    )


def test_console_application_environment_is_created(
    tmp_path: Path,
) -> None:
    request = DeveloperSetupRequest(
        destination=tmp_path / "ConsoleApplication",
        application_name="Console Application",
        email_mode="console",
        database_provider="sqlite",
        public_base_url=(
            "https://console.trycloudflare.com"
        ),
    )

    environment_path, _ = (
        prepare_application_environment(
            request
        )
    )
    environment_values = dotenv_values(
        environment_path
    )

    assert environment_values[
        "APP_DATABASE_URL"
    ] == "sqlite:///./console_application.db"
    jwt_secret_key = environment_values[
        "APP_JWT_SECRET_KEY"
    ]
    assert jwt_secret_key is not None
    assert len(jwt_secret_key) >= 32
    assert environment_values[
        "APP_SMTP_ENABLED"
    ] == "false"
    assert environment_values[
        "APP_PUBLIC_BASE_URL"
    ] == "https://console.trycloudflare.com"
    assert environment_values.get(
        "APP_SMTP_HOST"
    ) is None
    assert environment_values.get(
        "APP_SMTP_PASSWORD"
    ) is None


def test_gmail_application_environment_is_created(
    tmp_path: Path,
) -> None:
    entered_gmail_app_password = (
        "gmail app # password"
    )
    normalized_gmail_app_password = (
        "gmailapp#password"
    )
    request = DeveloperSetupRequest(
        destination=tmp_path / "GmailApplication",
        application_name="Gmail Application",
        email_mode="gmail",
        gmail_address="developer@gmail.com",
        gmail_app_password=entered_gmail_app_password,
        database_provider="sqlite",
    )

    environment_path, environment_example_path = (
        prepare_application_environment(
            request
        )
    )
    environment_values = dotenv_values(
        environment_path
    )

    assert environment_values[
        "APP_SMTP_ENABLED"
    ] == "true"
    assert environment_values[
        "APP_SMTP_HOST"
    ] == "smtp.gmail.com"
    assert environment_values[
        "APP_SMTP_PORT"
    ] == "587"
    assert environment_values[
        "APP_SMTP_USERNAME"
    ] == "developer@gmail.com"
    assert environment_values[
        "APP_SMTP_PASSWORD"
    ] == normalized_gmail_app_password
    assert environment_values[
        "APP_SMTP_SENDER_EMAIL"
    ] == "developer@gmail.com"
    assert environment_values[
        "APP_SMTP_SENDER_NAME"
    ] == "Gmail Application"
    assert environment_values[
        "APP_SMTP_SECURITY"
    ] == "starttls"

    assert normalized_gmail_app_password not in (
        environment_example_path.read_text(
            encoding="utf-8"
        )
    )


def test_custom_smtp_and_database_environment_is_created(
    tmp_path: Path,
) -> None:
    database_url = (
        "postgresql+psycopg://customer:secret@"
        "db.example.test:5432/customer_portal"
    )
    smtp_password = "smtp # password"
    request = DeveloperSetupRequest(
        destination=tmp_path / "SMTPApplication",
        application_name="SMTP Application",
        email_mode="smtp",
        smtp_host="smtp.example.test",
        smtp_port=465,
        smtp_security="ssl",
        smtp_username="smtp-user",
        smtp_password=smtp_password,
        smtp_sender_email="sender@example.test",
        smtp_sender_name="Customer Mail",
        database_provider="postgresql",
        database_url=database_url,
    )

    environment_path, environment_example_path = (
        prepare_application_environment(
            request
        )
    )
    environment_values = dotenv_values(
        environment_path
    )

    assert environment_values[
        "APP_DATABASE_URL"
    ] == database_url
    assert environment_values[
        "APP_SMTP_ENABLED"
    ] == "true"
    assert environment_values[
        "APP_SMTP_HOST"
    ] == "smtp.example.test"
    assert environment_values[
        "APP_SMTP_PORT"
    ] == "465"
    assert environment_values[
        "APP_SMTP_USERNAME"
    ] == "smtp-user"
    assert environment_values[
        "APP_SMTP_PASSWORD"
    ] == smtp_password
    assert environment_values[
        "APP_SMTP_SENDER_EMAIL"
    ] == "sender@example.test"
    assert environment_values[
        "APP_SMTP_SENDER_NAME"
    ] == "Customer Mail"
    assert environment_values[
        "APP_SMTP_SECURITY"
    ] == "ssl"

    environment_example_text = (
        environment_example_path.read_text(
            encoding="utf-8"
        )
    )
    assert database_url not in (
        environment_example_text
    )
    assert smtp_password not in (
        environment_example_text
    )


def test_smtp_without_authentication_environment_is_created(
    tmp_path: Path,
) -> None:
    request = DeveloperSetupRequest(
        destination=tmp_path / "SMTPWithoutAuthentication",
        application_name="Internal Mail Application",
        email_mode="smtp",
        smtp_host="mail.internal.test",
        smtp_port=25,
        smtp_security="none",
        smtp_sender_email="sender@internal.test",
        database_provider="sqlite",
    )

    environment_path, _ = (
        prepare_application_environment(
            request
        )
    )
    environment_values = dotenv_values(
        environment_path
    )

    assert environment_values[
        "APP_SMTP_ENABLED"
    ] == "true"
    assert environment_values[
        "APP_SMTP_HOST"
    ] == "mail.internal.test"
    assert environment_values[
        "APP_SMTP_PORT"
    ] == "25"
    assert environment_values[
        "APP_SMTP_SECURITY"
    ] == "none"
    assert environment_values.get(
        "APP_SMTP_USERNAME"
    ) is None
    assert environment_values.get(
        "APP_SMTP_PASSWORD"
    ) is None
