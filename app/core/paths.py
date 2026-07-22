import os
import sys
from pathlib import Path


APPLICATION_DATA_DIRECTORY_NAME = (
    "ApplicationStarterPlatform"
)

APPLICATION_DATABASE_FILENAME = (
    "application_starter_platform.db"
)


def is_bundled_application() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_resource_directory() -> Path:
    if is_bundled_application():
        bundle_directory = getattr(
            sys,
            "_MEIPASS",
            None,
        )

        if bundle_directory is None:
            raise RuntimeError(
                "The bundled resource directory is unavailable."
            )

        return Path(bundle_directory)

    return Path(__file__).resolve().parents[2]


def get_data_directory() -> Path:
    configured_directory = os.getenv(
        "APP_DATA_DIRECTORY"
    )

    if configured_directory:
        return Path(
            configured_directory
        ).expanduser().resolve()

    if not is_bundled_application():
        return get_resource_directory()

    local_application_data = os.getenv(
        "LOCALAPPDATA"
    )

    if local_application_data:
        base_directory = Path(
            local_application_data
        )
    else:
        base_directory = (
            Path.home()
            / "AppData"
            / "Local"
        )

    return (
        base_directory
        / APPLICATION_DATA_DIRECTORY_NAME
        / "Data"
    )


def get_environment_file_path() -> Path:
    return get_data_directory() / ".env"


def get_database_file_path() -> Path:
    return (
        get_data_directory()
        / APPLICATION_DATABASE_FILENAME
    )


def get_default_database_url() -> str:
    database_path = get_database_file_path()

    return f"sqlite:///{database_path.as_posix()}"


def get_frontend_directory() -> Path:
    return get_resource_directory() / "frontend"


def get_migrations_directory() -> Path:
    return get_resource_directory() / "migrations"


def get_alembic_config_path() -> Path:
    return get_resource_directory() / "alembic.ini"

def get_application_manifest_path() -> Path:
    configured_path = os.getenv(
        "APP_MANIFEST_PATH"
    )

    if configured_path:
        return Path(
            configured_path
        ).expanduser().resolve()

    return (
        get_resource_directory()
        / "application_manifest.yaml"
    )
