"""Engine used by the Developer Setup installer."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import re
from secrets import token_urlsafe
from shutil import (
    copy2,
    copytree,
    ignore_patterns,
)
import sys
from typing import Literal
import unicodedata
from urllib.parse import urlsplit
from uuid import UUID, uuid5

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.core.manifest import ApplicationManifest
from app.db.providers import (
    DatabaseProviderId,
    get_database_provider_profile,
)


PROJECT_TEMPLATE_ITEMS = (
    ".env.example",
    ".gitignore",
    "ApplicationStarterPlatform.spec",
    "LICENSE",
    "README.md",
    "alembic.ini",
    "app",
    "application_manifest.yaml",
    "export_openapi.py",
    "frontend",
    "installer.iss",
    "migrations",
    "pyproject.toml",
    "run.py",
    "tests",
)


TEMPLATE_IGNORE = ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "test_developer_setup.py",
    "test_developer_setup_gui.py",
)

DATABASE_DRIVER_DEPENDENCY_MARKER = (
    "# DATABASE_PROVIDER_DRIVER_DEPENDENCY"
)

DATABASE_URL_EXAMPLE_MARKER = (
    "# DATABASE_PROVIDER_URL_EXAMPLE"
)

INSTALLER_ID_NAMESPACE = UUID(
    "E5D76C2B-4D8C-4EB5-97AD-F79B9A69A1F1"
)

DEFAULT_PUBLIC_BASE_URL = "http://127.0.0.1:8000"


class DeveloperSetupRequest(BaseModel):
    """Validated choices received from the installer."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    destination: Path
    application_name: str = Field(min_length=1)

    email_mode: Literal[
        "gmail",
        "smtp",
        "console",
    ]

    gmail_address: str | None = Field(
        default=None,
        min_length=1,
    )
    gmail_app_password: SecretStr | None = None

    smtp_host: str | None = Field(
        default=None,
        min_length=1,
    )
    smtp_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )
    smtp_security: Literal[
        "starttls",
        "ssl",
        "none",
    ] | None = None
    smtp_username: str | None = Field(
        default=None,
        min_length=1,
    )
    smtp_password: SecretStr | None = None
    smtp_sender_email: str | None = Field(
        default=None,
        min_length=1,
    )
    smtp_sender_name: str | None = Field(
        default=None,
        min_length=1,
    )

    database_provider: DatabaseProviderId
    database_url: SecretStr | None = None
    public_base_url: str = DEFAULT_PUBLIC_BASE_URL

    @field_validator(
        "gmail_app_password",
        mode="before",
    )
    @classmethod
    def normalize_gmail_app_password(
        cls,
        value: object,
    ) -> object:
        if value is None:
            return None

        if isinstance(value, SecretStr):
            raw_value = value.get_secret_value()
        elif isinstance(value, str):
            raw_value = value
        else:
            return value

        normalized_value = "".join(
            raw_value.split()
        )

        if not normalized_value:
            return None

        return normalized_value

    @field_validator(
        "public_base_url",
        mode="before",
    )
    @classmethod
    def validate_public_base_url(
        cls,
        value: object,
    ) -> object:
        if not isinstance(value, str):
            return value

        return normalize_public_base_url(value)

    @model_validator(mode="after")
    def validate_email_configuration(
        self,
    ) -> "DeveloperSetupRequest":
        gmail_fields = (
            self.gmail_address,
            self.gmail_app_password,
        )
        smtp_fields = (
            self.smtp_host,
            self.smtp_port,
            self.smtp_security,
            self.smtp_username,
            self.smtp_password,
            self.smtp_sender_email,
            self.smtp_sender_name,
        )

        if self.email_mode == "gmail":
            if any(
                value is not None
                for value in smtp_fields
            ):
                raise ValueError(
                    "Gmail mode does not accept "
                    "custom SMTP fields."
                )

            gmail_password_is_missing = (
                self.gmail_app_password is None
                or not (
                    self.gmail_app_password
                    .get_secret_value()
                    .strip()
                )
            )

            if (
                self.gmail_address is None
                or not self.gmail_address.strip()
                or gmail_password_is_missing
            ):
                raise ValueError(
                    "Gmail address and App Password "
                    "are required for Gmail mode."
                )

        elif self.email_mode == "smtp":
            if any(
                value is not None
                for value in gmail_fields
            ):
                raise ValueError(
                    "SMTP mode does not accept "
                    "Gmail fields."
                )

            if (
                self.smtp_host is None
                or not self.smtp_host.strip()
                or self.smtp_port is None
                or self.smtp_security is None
                or self.smtp_sender_email is None
                or not self.smtp_sender_email.strip()
            ):
                raise ValueError(
                    "SMTP host, port, security, and "
                    "sender email are required "
                    "for SMTP mode."
                )

            has_smtp_username = (
                self.smtp_username is not None
                and bool(self.smtp_username.strip())
            )
            has_smtp_password = (
                self.smtp_password is not None
                and bool(
                    self.smtp_password
                    .get_secret_value()
                    .strip()
                )
            )

            if (
                has_smtp_username
                != has_smtp_password
            ):
                raise ValueError(
                    "SMTP username and password "
                    "must be provided together."
                )

        else:
            if any(
                value is not None
                for value in (
                    *gmail_fields,
                    *smtp_fields,
                )
            ):
                raise ValueError(
                    "Console email mode does not accept "
                    "email configuration fields."
                )

        return self

    @model_validator(mode="after")
    def validate_database_configuration(
        self,
    ) -> "DeveloperSetupRequest":
        provider_profile = (
            get_database_provider_profile(
                self.database_provider
            )
        )

        if self.database_url is None:
            if (
                self.database_provider
                != DatabaseProviderId.SQLITE
            ):
                raise ValueError(
                    "Database URL is required for "
                    "non-SQLite providers."
                )

            return self

        database_url = (
            self.database_url
            .get_secret_value()
            .strip()
        )

        if not database_url:
            raise ValueError(
                "Database URL must not be empty."
            )

        provider_profile.validate_database_url(
            database_url
        )

        return self


def create_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Create a new application from "
            "Application Starter Developer."
        )
    )

    parser.add_argument(
        "--destination",
        required=True,
        type=Path,
        help="Folder in which the application is created.",
    )

    parser.add_argument(
        "--application-name",
        required=True,
        help="Display name of the new application.",
    )

    parser.add_argument(
        "--email-mode",
        required=True,
        choices=[
            "gmail",
            "smtp",
            "console",
        ],
    )

    parser.add_argument(
        "--gmail-address",
        help="Gmail address used for sending email.",
    )

    parser.add_argument(
        "--gmail-app-password",
        help="Gmail App Password.",
    )

    parser.add_argument(
        "--smtp-host",
        help="Custom SMTP server host.",
    )

    parser.add_argument(
        "--smtp-port",
        type=int,
        help="Custom SMTP server port.",
    )

    parser.add_argument(
        "--smtp-security",
        choices=[
            "starttls",
            "ssl",
            "none",
        ],
        help="Custom SMTP connection security.",
    )

    parser.add_argument(
        "--smtp-username",
        help="Custom SMTP username.",
    )

    parser.add_argument(
        "--smtp-password",
        help="Custom SMTP password.",
    )

    parser.add_argument(
        "--smtp-sender-email",
        help="Custom SMTP sender email address.",
    )

    parser.add_argument(
        "--smtp-sender-name",
        help="Custom SMTP sender display name.",
    )

    parser.add_argument(
        "--database-provider",
        required=True,
        choices=[
            provider.value
            for provider in DatabaseProviderId
        ],
    )


    parser.add_argument(
        "--database-url",
        help=(
            "SQLAlchemy database URL. Required "
            "for non-SQLite providers."
        ),
    )

    parser.add_argument(
        "--public-base-url",
        default=DEFAULT_PUBLIC_BASE_URL,
        help=(
            "Browser-facing application URL. Public hosts "
            "must use HTTPS."
        ),
    )

    return parser


def normalize_optional_argument(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()

    if not normalized_value:
        return None

    return normalized_value


def normalize_public_base_url(
    value: str,
) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            "Application URL is required."
        )

    parsed_url = urlsplit(normalized_value)

    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or parsed_url.hostname is None
    ):
        raise ValueError(
            "Application URL must be a complete http:// "
            "or https:// URL."
        )

    try:
        parsed_url.port
    except ValueError as error:
        raise ValueError(
            "Application URL contains an invalid port."
        ) from error

    if (
        parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
        or parsed_url.path not in {"", "/"}
    ):
        raise ValueError(
            "Application URL must contain only the scheme, "
            "host, and optional port."
        )

    local_hosts = {
        "127.0.0.1",
        "::1",
        "localhost",
    }

    if (
        parsed_url.hostname.lower() not in local_hosts
        and parsed_url.scheme != "https"
    ):
        raise ValueError(
            "A public application URL must use HTTPS."
        )

    return (
        f"{parsed_url.scheme}://{parsed_url.netloc}"
    )


def parse_setup_request() -> DeveloperSetupRequest:
    arguments = create_argument_parser().parse_args()

    return DeveloperSetupRequest(
        destination=(
            arguments.destination
            .expanduser()
            .resolve()
        ),
        application_name=(
            arguments.application_name.strip()
        ),
        email_mode=arguments.email_mode,
        gmail_address=normalize_optional_argument(
            arguments.gmail_address
        ),
        gmail_app_password=(
            arguments.gmail_app_password
        ),
        smtp_host=normalize_optional_argument(
            arguments.smtp_host
        ),
        smtp_port=arguments.smtp_port,
        smtp_security=arguments.smtp_security,
        smtp_username=normalize_optional_argument(
            arguments.smtp_username
        ),
        smtp_password=arguments.smtp_password,
        smtp_sender_email=normalize_optional_argument(
            arguments.smtp_sender_email
        ),
        smtp_sender_name=normalize_optional_argument(
            arguments.smtp_sender_name
        ),
        database_provider=arguments.database_provider,
        database_url=arguments.database_url,
        public_base_url=arguments.public_base_url,
    )


def validate_destination_directory(
    destination: Path,
) -> None:
    if not destination.exists():
        return

    if not destination.is_dir():
        raise RuntimeError(
            "The selected destination is not a folder: "
            f"{destination}"
        )

    if any(destination.iterdir()):
        raise RuntimeError(
            "The selected destination folder is not empty: "
            f"{destination}"
        )


def get_project_template_directory() -> Path:
    if bool(getattr(sys, "frozen", False)):
        bundle_directory = getattr(
            sys,
            "_MEIPASS",
            None,
        )

        if bundle_directory is None:
            raise RuntimeError(
                "The bundled project template "
                "directory is unavailable."
            )

        return Path(bundle_directory)

    return Path(__file__).resolve().parent


def validate_project_template(
    template_directory: Path,
) -> None:
    missing_items = [
        item_name
        for item_name in PROJECT_TEMPLATE_ITEMS
        if not (
            template_directory
            / item_name
        ).exists()
    ]

    if missing_items:
        missing_text = ", ".join(
            missing_items
        )

        raise RuntimeError(
            "The Developer Setup template is incomplete. "
            f"Missing items: {missing_text}"
        )


def create_project_files(
    request: DeveloperSetupRequest,
    template_directory: Path | None = None,
) -> None:
    source_directory = (
        template_directory
        if template_directory is not None
        else get_project_template_directory()
    )

    validate_destination_directory(
        request.destination
    )
    validate_project_template(
        source_directory
    )

    request.destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        for item_name in PROJECT_TEMPLATE_ITEMS:
            source_path = (
                source_directory
                / item_name
            )
            destination_path = (
                request.destination
                / item_name
            )

            if source_path.is_dir():
                copytree(
                    source_path,
                    destination_path,
                    ignore=TEMPLATE_IGNORE,
                )
            else:
                copy2(
                    source_path,
                    destination_path,
                )
    except OSError as error:
        raise RuntimeError(
            "The application files could not be created "
            f"in: {request.destination}"
        ) from error

def configure_database_dependencies(
    request: DeveloperSetupRequest,
) -> None:
    pyproject_path = (
        request.destination
        / "pyproject.toml"
    )

    try:
        pyproject_text = pyproject_path.read_text(
            encoding="utf-8"
        )
    except OSError as error:
        raise RuntimeError(
            "The generated pyproject.toml "
            "could not be read."
        ) from error

    marker_count = pyproject_text.count(
        DATABASE_DRIVER_DEPENDENCY_MARKER
    )

    if marker_count != 1:
        raise RuntimeError(
            "The generated pyproject.toml must "
            "contain exactly one database "
            "provider dependency marker."
        )

    provider_profile = (
        get_database_provider_profile(
            request.database_provider
        )
    )
    driver_dependency = (
        provider_profile.driver_distribution
    )

    replacement = (
        f'"{driver_dependency}",'
        if driver_dependency is not None
        else ""
    )

    configured_pyproject_text = (
        pyproject_text.replace(
            DATABASE_DRIVER_DEPENDENCY_MARKER,
            replacement,
        )
    )

    try:
        pyproject_path.write_text(
            configured_pyproject_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The generated pyproject.toml "
            "could not be updated."
        ) from error


def configure_database_environment_example(
    request: DeveloperSetupRequest,
) -> None:
    environment_example_path = (
        request.destination
        / ".env.example"
    )

    try:
        environment_example_text = (
            environment_example_path.read_text(
                encoding="utf-8"
            )
        )
    except OSError as error:
        raise RuntimeError(
            "The generated .env.example "
            "could not be read."
        ) from error

    environment_example_lines = (
        environment_example_text.splitlines(
            keepends=True
        )
    )

    marker_indexes = [
        index
        for index, line
        in enumerate(environment_example_lines)
        if line.strip()
        == DATABASE_URL_EXAMPLE_MARKER
    ]

    if len(marker_indexes) != 1:
        raise RuntimeError(
            "The generated .env.example must "
            "contain exactly one database "
            "provider URL example marker."
        )

    marker_index = marker_indexes[0]
    database_url_index = marker_index + 1

    if (
        database_url_index
        >= len(environment_example_lines)
    ):
        raise RuntimeError(
            "The database provider URL example "
            "marker must be followed by "
            "APP_DATABASE_URL."
        )

    database_url_line = (
        environment_example_lines[
            database_url_index
        ]
    )
    database_url_line_without_ending = (
        database_url_line.rstrip("\r\n")
    )

    if not database_url_line_without_ending.startswith(
        "APP_DATABASE_URL="
    ):
        raise RuntimeError(
            "The database provider URL example "
            "marker must be followed by "
            "APP_DATABASE_URL."
        )

    line_ending = database_url_line[
        len(database_url_line_without_ending):
    ]

    environment_example_lines[marker_index] = ""
    environment_example_lines[
        database_url_index
    ] = (
        "APP_DATABASE_URL="
        f"{create_database_url_example(request)}"
        f"{line_ending}"
    )

    configured_environment_example_text = "".join(
        environment_example_lines
    )

    try:
        environment_example_path.write_text(
            configured_environment_example_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The generated .env.example "
            "could not be updated."
        ) from error


def create_application_slug(
    request: DeveloperSetupRequest,
) -> str:
    possible_names = (
        request.application_name,
        request.destination.name,
    )

    for possible_name in possible_names:
        normalized_name = unicodedata.normalize(
            "NFKD",
            possible_name,
        )
        ascii_name = normalized_name.encode(
            "ascii",
            errors="ignore",
        ).decode("ascii")

        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            ascii_name.lower(),
        ).strip("-")

        if slug:
            return slug

    name_hash = sha256(
        request.application_name.encode("utf-8")
    ).hexdigest()[:12]

    return f"application-{name_hash}"


def create_application_technical_name(
    request: DeveloperSetupRequest,
) -> str:
    return "".join(
        part.capitalize()
        for part in create_application_slug(
            request
        ).split("-")
    )


def create_application_database_filename(
    request: DeveloperSetupRequest,
) -> str:
    application_slug = create_application_slug(
        request
    )

    return (
        f"{application_slug.replace('-', '_')}.db"
    )


def create_database_url_example(
    request: DeveloperSetupRequest,
) -> str:
    if (
        request.database_provider
        == DatabaseProviderId.SQLITE
    ):
        return (
            "sqlite:///./"
            f"{create_application_database_filename(request)}"
        )

    return get_database_provider_profile(
        request.database_provider
    ).database_url_example


def create_application_installer_id(
    request: DeveloperSetupRequest,
) -> str:
    return str(
        uuid5(
            INSTALLER_ID_NAMESPACE,
            create_application_slug(request),
        )
    ).upper()


def replace_exact_template_values(
    file_path: Path,
    replacements: tuple[
        tuple[str, str, int],
        ...,
    ],
) -> None:
    try:
        file_text = file_path.read_text(
            encoding="utf-8"
        )
    except OSError as error:
        raise RuntimeError(
            "The generated runtime template "
            f"could not be read: {file_path.name}"
        ) from error

    for (
        original_value,
        configured_value,
        expected_count,
    ) in replacements:
        actual_count = file_text.count(
            original_value
        )

        if actual_count != expected_count:
            raise RuntimeError(
                "The generated runtime template "
                "contains an unexpected number of "
                f"{original_value!r} values in "
                f"{file_path.name}: expected "
                f"{expected_count}, found "
                f"{actual_count}."
            )

        file_text = file_text.replace(
            original_value,
            configured_value,
        )

    try:
        file_path.write_text(
            file_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The generated runtime template "
            f"could not be updated: {file_path.name}"
        ) from error


def configure_runtime_identity(
    request: DeveloperSetupRequest,
) -> None:
    application_slug = create_application_slug(
        request
    )
    technical_name = (
        create_application_technical_name(
            request
        )
    )
    database_filename = (
        create_application_database_filename(
            request
        )
    )
    installer_id = create_application_installer_id(
        request
    )

    replace_exact_template_values(
        request.destination
        / "app"
        / "core"
        / "paths.py",
        (
            (
                '"ApplicationStarterPlatform"',
                f'"{technical_name}"',
                1,
            ),
            (
                '"application_starter_platform.db"',
                f'"{database_filename}"',
                1,
            ),
        ),
    )

    replace_exact_template_values(
        request.destination
        / "ApplicationStarterPlatform.spec",
        (
            (
                'name="ApplicationStarterPlatform"',
                f'name="{technical_name}"',
                2,
            ),
        ),
    )

    replace_exact_template_values(
        request.destination / "installer.iss",
        (
            (
                "AppId={{"
                "E5D76C2B-4D8C-4EB5-97AD-"
                "F79B9A69A1F1}",
                "AppId={{" + installer_id + "}",
                1,
            ),
            (
                "Application Starter Platform",
                request.application_name,
                3,
            ),
            (
                "ApplicationStarterPlatform",
                technical_name,
                7,
            ),
            (
                "application-starter-platform",
                application_slug,
                2,
            ),
        ),
    )


def configure_application_environment_example(
    request: DeveloperSetupRequest,
) -> None:
    environment_example_path = (
        request.destination
        / ".env.example"
    )

    try:
        environment_example_text = (
            environment_example_path.read_text(
                encoding="utf-8"
            )
        )
    except OSError as error:
        raise RuntimeError(
            "The generated .env.example "
            "could not be read."
        ) from error

    application_slug = create_application_slug(
        request
    )
    smtp_sender_name = (
        request.smtp_sender_name
        or request.application_name
    )

    environment_values = (
        (
            "APP_APP_NAME",
            request.application_name,
        ),
        (
            "APP_APP_VERSION",
            "0.1.0",
        ),
        (
            "APP_JWT_ISSUER",
            application_slug,
        ),
        (
            "APP_JWT_AUDIENCE",
            f"{application_slug}-api",
        ),
        (
            "APP_PUBLIC_BASE_URL",
            request.public_base_url,
        ),
        (
            "APP_SMTP_SENDER_NAME",
            smtp_sender_name,
        ),
    )

    environment_example_lines = (
        environment_example_text.splitlines(
            keepends=True
        )
    )

    for variable_name, variable_value in (
        environment_values
    ):
        variable_prefix = (
            f"{variable_name}="
        )
        variable_indexes = [
            index
            for index, line
            in enumerate(
                environment_example_lines
            )
            if line.rstrip(
                "\r\n"
            ).startswith(
                variable_prefix
            )
        ]

        if len(variable_indexes) != 1:
            raise RuntimeError(
                "The generated .env.example must "
                "contain exactly one "
                f"{variable_name} setting."
            )

        variable_index = variable_indexes[0]
        original_line = (
            environment_example_lines[
                variable_index
            ]
        )
        original_line_without_ending = (
            original_line.rstrip("\r\n")
        )
        line_ending = original_line[
            len(original_line_without_ending):
        ]

        environment_example_lines[
            variable_index
        ] = (
            f"{variable_name}="
            f"{variable_value}"
            f"{line_ending}"
        )

    configured_environment_example_text = "".join(
        environment_example_lines
    )

    try:
        environment_example_path.write_text(
            configured_environment_example_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The generated .env.example "
            "could not be updated."
        ) from error


def create_application_environment(
    request: DeveloperSetupRequest,
) -> None:
    environment_example_path = (
        request.destination
        / ".env.example"
    )
    environment_path = (
        request.destination
        / ".env"
    )

    try:
        environment_example_text = (
            environment_example_path.read_text(
                encoding="utf-8"
            )
        )
    except OSError as error:
        raise RuntimeError(
            "The configured .env.example "
            "could not be read."
        ) from error

    if request.database_url is None:
        database_url = create_database_url_example(
            request
        )
    else:
        database_url = (
            request.database_url
            .get_secret_value()
            .strip()
        )

    email_environment_values: list[
        tuple[str, str]
    ]

    if request.email_mode == "console":
        email_environment_values = [
            (
                "APP_SMTP_ENABLED",
                "false",
            ),
            (
                "APP_SMTP_SENDER_NAME",
                request.application_name,
            ),
        ]
    elif request.email_mode == "gmail":
        if (
            request.gmail_address is None
            or request.gmail_app_password is None
        ):
            raise RuntimeError(
                "The validated Gmail configuration "
                "is incomplete."
            )

        email_environment_values = [
            (
                "APP_SMTP_ENABLED",
                "true",
            ),
            (
                "APP_SMTP_HOST",
                "smtp.gmail.com",
            ),
            (
                "APP_SMTP_PORT",
                "587",
            ),
            (
                "APP_SMTP_USERNAME",
                request.gmail_address,
            ),
            (
                "APP_SMTP_PASSWORD",
                request.gmail_app_password
                .get_secret_value(),
            ),
            (
                "APP_SMTP_SENDER_EMAIL",
                request.gmail_address,
            ),
            (
                "APP_SMTP_SENDER_NAME",
                request.application_name,
            ),
            (
                "APP_SMTP_SECURITY",
                "starttls",
            ),
        ]
    else:
        if (
            request.smtp_host is None
            or request.smtp_port is None
            or request.smtp_security is None
            or request.smtp_sender_email is None
        ):
            raise RuntimeError(
                "The validated SMTP configuration "
                "is incomplete."
            )

        email_environment_values = [
            (
                "APP_SMTP_ENABLED",
                "true",
            ),
            (
                "APP_SMTP_HOST",
                request.smtp_host,
            ),
            (
                "APP_SMTP_PORT",
                str(request.smtp_port),
            ),
            (
                "APP_SMTP_SENDER_EMAIL",
                request.smtp_sender_email,
            ),
            (
                "APP_SMTP_SENDER_NAME",
                (
                    request.smtp_sender_name
                    or request.application_name
                ),
            ),
            (
                "APP_SMTP_SECURITY",
                request.smtp_security,
            ),
        ]

        if request.smtp_username is not None:
            if request.smtp_password is None:
                raise RuntimeError(
                    "The validated SMTP credentials "
                    "are incomplete."
                )

            email_environment_values.extend(
                [
                    (
                        "APP_SMTP_USERNAME",
                        request.smtp_username,
                    ),
                    (
                        "APP_SMTP_PASSWORD",
                        request.smtp_password
                        .get_secret_value(),
                    ),
                ]
            )

    environment_values = [
        (
            "APP_DATABASE_URL",
            database_url,
        ),
        (
            "APP_JWT_SECRET_KEY",
            token_urlsafe(48),
        ),
        *email_environment_values,
    ]

    environment_lines = (
        environment_example_text.splitlines(
            keepends=True
        )
    )

    for variable_name, variable_value in (
        environment_values
    ):
        active_prefix = f"{variable_name}="
        commented_prefix = (
            f"# {variable_name}="
        )
        variable_indexes = [
            index
            for index, line
            in enumerate(environment_lines)
            if (
                line.rstrip("\r\n").startswith(
                    active_prefix
                )
                or line.rstrip("\r\n").startswith(
                    commented_prefix
                )
            )
        ]

        if len(variable_indexes) != 1:
            raise RuntimeError(
                "The configured .env.example must "
                "contain exactly one "
                f"{variable_name} setting."
            )

        variable_index = variable_indexes[0]
        original_line = environment_lines[
            variable_index
        ]
        original_line_without_ending = (
            original_line.rstrip("\r\n")
        )
        line_ending = original_line[
            len(original_line_without_ending):
        ]
        serialized_value = json.dumps(
            variable_value,
            ensure_ascii=False,
        )

        environment_lines[variable_index] = (
            f"{variable_name}="
            f"{serialized_value}"
            f"{line_ending}"
        )

    environment_text = "".join(
        environment_lines
    )

    try:
        environment_path.write_text(
            environment_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The application .env file "
            "could not be written."
        ) from error


def configure_application_manifest(
    request: DeveloperSetupRequest,
) -> None:
    manifest_path = (
        request.destination
        / "application_manifest.yaml"
    )

    try:
        manifest_data = yaml.safe_load(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, yaml.YAMLError) as error:
        raise RuntimeError(
            "The generated application manifest "
            "could not be read."
        ) from error

    if not isinstance(manifest_data, dict):
        raise RuntimeError(
            "The generated application manifest "
            "is invalid."
        )

    application_slug = create_application_slug(
        request
    )
    technical_name = (
        create_application_technical_name(
            request
        )
    )

    manifest_data["application"]["name"] = (
        request.application_name
    )
    manifest_data["application"]["slug"] = (
        application_slug
    )
    manifest_data["application"]["version"] = "0.1.0"
    manifest_data["application"]["description"] = (
        f"{request.application_name} application."
    )

    manifest_data["data"]["directory_name"] = (
        technical_name
    )

    database_section = manifest_data["database"]
    database_section["provider"] = (
        request.database_provider.value
    )
    database_section.pop("engine", None)
    database_section.pop("sqlite_filename", None)

    manifest_data["email"]["mode"] = (
        request.email_mode
    )
    manifest_data["email"]["from_name"] = (
        request.smtp_sender_name
        or request.application_name
    )

    manifest_data["packaging"]["executable_name"] = (
        technical_name
    )
    manifest_data["packaging"]["installer_name"] = (
        f"{technical_name}_Setup"
    )

    try:
        validated_manifest = (
            ApplicationManifest.model_validate(
                manifest_data
            )
        )
    except Exception as error:
        raise RuntimeError(
            "The generated application manifest "
            "failed validation."
        ) from error

    manifest_text = yaml.safe_dump(
        validated_manifest.model_dump(
            mode="json",
            exclude_none=True,
        ),
        sort_keys=False,
        allow_unicode=True,
    )

    try:
        manifest_path.write_text(
            manifest_text,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(
            "The generated application manifest "
            "could not be written."
        ) from error


def display_setup_summary(
    request: DeveloperSetupRequest,
) -> None:
    print("Developer Setup request validated")
    print(f"Destination: {request.destination}")
    print(
        "Application name: "
        f"{request.application_name}"
    )
    print(f"Email mode: {request.email_mode}")
    print(
        "Database provider: "
        f"{request.database_provider.value}"
    )
    print(
        "Application URL: "
        f"{request.public_base_url}"
    )


def create_application_project(
    request: DeveloperSetupRequest,
    template_directory: Path | None = None,
) -> None:
    create_project_files(
        request,
        template_directory=template_directory,
    )
    configure_runtime_identity(request)
    configure_database_dependencies(request)
    configure_database_environment_example(request)
    configure_application_environment_example(request)
    create_application_environment(request)
    configure_application_manifest(request)


def main() -> None:
    request = parse_setup_request()

    display_setup_summary(request)
    create_application_project(request)

    print(
        "Application project created successfully: "
        f"{request.destination}"
    )


if __name__ == "__main__":
    main()
