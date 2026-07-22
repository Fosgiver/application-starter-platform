from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

import app.models
from app.core.manifest import (
    get_application_manifest,
)
from app.core.settings import settings
from app.db.base import Base
from app.db.engine_factory import (
    create_database_engine,
)
from app.db.migration_runner import (
    DATABASE_PROVIDER_ATTRIBUTE,
    DATABASE_URL_ATTRIBUTE,
)
from app.db.providers import (
    get_database_provider_profile,
)


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = config.attributes.get(
    DATABASE_URL_ATTRIBUTE,
    settings.database_url,
)

if (
    not isinstance(database_url, str)
    or not database_url.strip()
):
    raise RuntimeError(
        "A valid database URL is required "
        "to run migrations."
    )

database_provider = config.attributes.get(
    DATABASE_PROVIDER_ATTRIBUTE
)

if database_provider is None:
    application_manifest = (
        get_application_manifest()
    )
    database_provider = (
        application_manifest.database.provider
    )

if (
    not isinstance(database_provider, str)
    or not database_provider.strip()
):
    raise RuntimeError(
        "A valid database provider is required "
        "to run migrations."
    )

provider_profile = (
    get_database_provider_profile(
        database_provider
    )
)

provider_profile.validate_database_url(
    database_url
)

config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_database_engine(
        database_url=database_url,
        provider_id=database_provider,
        echo=False,
        additional_engine_options={
            "poolclass": pool.NullPool,
        },
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()