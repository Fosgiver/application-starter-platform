from alembic import command
from alembic.config import Config

from app.core.manifest import (
    get_application_manifest,
)
from app.core.paths import (
    get_alembic_config_path,
    get_data_directory,
    get_migrations_directory,
)
from app.core.settings import settings
from app.db.providers import (
    DatabaseProviderId,
    get_database_provider_profile,
)


DATABASE_URL_ATTRIBUTE = (
    "application_database_url"
)

DATABASE_PROVIDER_ATTRIBUTE = (
    "application_database_provider"
)


def create_alembic_config(
    database_url: str,
    provider_id: DatabaseProviderId | str,
) -> Config:
    if not database_url.strip():
        raise ValueError(
            "database_url must not be empty."
        )

    provider_profile = (
        get_database_provider_profile(
            provider_id
        )
    )

    provider_profile.validate_database_url(
        database_url
    )

    alembic_config = Config(
        str(get_alembic_config_path())
    )

    alembic_config.set_main_option(
        "script_location",
        get_migrations_directory().as_posix(),
    )

    alembic_config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )

    alembic_config.attributes[
        DATABASE_URL_ATTRIBUTE
    ] = database_url

    alembic_config.attributes[
        DATABASE_PROVIDER_ATTRIBUTE
    ] = provider_profile.provider_id

    return alembic_config


def run_database_migrations() -> None:
    get_data_directory().mkdir(
        parents=True,
        exist_ok=True,
    )

    application_manifest = (
        get_application_manifest()
    )

    alembic_config = create_alembic_config(
        database_url=settings.database_url,
        provider_id=(
            application_manifest.database.provider
        ),
    )

    command.upgrade(
        alembic_config,
        "head",
    )