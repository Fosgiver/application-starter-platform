from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import (
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

from app.db.migration_runner import (
    DATABASE_PROVIDER_ATTRIBUTE,
    DATABASE_URL_ATTRIBUTE,
    create_alembic_config,
)
from app.db.providers import (
    DatabaseProviderId,
    SQLITE_PROVIDER_PROFILE,
)


def get_table_names(
    database_url: str,
) -> set[str]:
    engine = create_engine(
        database_url
    )

    try:
        return set(
            inspect(engine).get_table_names()
        )
    finally:
        engine.dispose()


def get_column_names(
    database_url: str,
    table_name: str,
) -> set[str]:
    engine = create_engine(
        database_url
    )

    try:
        columns = inspect(engine).get_columns(
            table_name
        )

        return {
            column["name"]
            for column in columns
        }
    finally:
        engine.dispose()


def get_current_revision(
    database_url: str,
) -> str | None:
    engine = create_engine(
        database_url
    )

    try:
        with engine.connect() as connection:
            table_names = set(
                inspect(connection).get_table_names()
            )

            if "alembic_version" not in table_names:
                return None

            return connection.execute(
                text(
                    "SELECT version_num "
                    "FROM alembic_version"
                )
            ).scalar_one_or_none()
    finally:
        engine.dispose()


def test_alembic_config_carries_provider_context(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "provider_context.db"
    )
    database_url = (
        "sqlite:///"
        f"{database_path.as_posix()}"
    )

    alembic_config = create_alembic_config(
        database_url=database_url,
        provider_id=DatabaseProviderId.SQLITE,
    )

    assert (
        alembic_config.attributes[
            DATABASE_URL_ATTRIBUTE
        ]
        == database_url
    )
    assert (
        alembic_config.attributes[
            DATABASE_PROVIDER_ATTRIBUTE
        ]
        == DatabaseProviderId.SQLITE
    )


def test_alembic_config_rejects_provider_url_mismatch(
) -> None:
    database_url = (
        "postgresql+psycopg://"
        "user:password@localhost/database"
    )

    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        create_alembic_config(
            database_url=database_url,
            provider_id=DatabaseProviderId.SQLITE,
        )


def test_online_migrations_use_provider_engine_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = (
        tmp_path
        / "provider_configured_migration.db"
    )
    database_url = (
        "sqlite:///"
        f"{database_path.as_posix()}"
    )

    configured_database_paths: list[
        str | None
    ] = []

    provider_class = type(
        SQLITE_PROVIDER_PROFILE
    )
    original_configure_engine = (
        provider_class.configure_engine
    )

    def track_configured_engine(
        self: object,
        engine: Engine,
    ) -> None:
        configured_database_paths.append(
            engine.url.database
        )

        original_configure_engine(
            self,
            engine,
        )

    monkeypatch.setattr(
        provider_class,
        "configure_engine",
        track_configured_engine,
    )

    alembic_config = create_alembic_config(
        database_url=database_url,
        provider_id=DatabaseProviderId.SQLITE,
    )

    command.upgrade(
        alembic_config,
        "head",
    )

    assert (
        database_path.as_posix()
        in configured_database_paths
    )


def test_sqlite_migration_lifecycle(
    tmp_path: Path,
) -> None:
    database_path = (
        tmp_path
        / "migration_lifecycle.db"
    )
    database_url = (
        "sqlite:///"
        f"{database_path.as_posix()}"
    )

    alembic_config = create_alembic_config(
        database_url=database_url,
        provider_id=DatabaseProviderId.SQLITE,
    )

    script_directory = (
        ScriptDirectory.from_config(
            alembic_config
        )
    )
    expected_head = (
        script_directory.get_current_head()
    )

    assert expected_head is not None

    command.upgrade(
        alembic_config,
        "head",
    )

    assert database_path.is_file()

    table_names = get_table_names(
        database_url
    )

    assert "users" in table_names
    assert "account_tokens" in table_names
    assert "alembic_version" in table_names

    user_columns = get_column_names(
        database_url,
        "users",
    )
    account_token_columns = get_column_names(
        database_url,
        "account_tokens",
    )

    assert "must_change_password" not in (
        user_columns
    )
    assert "revoked_at" in (
        account_token_columns
    )

    assert get_current_revision(
        database_url
    ) == expected_head

    command.downgrade(
        alembic_config,
        "base",
    )

    table_names_after_downgrade = (
        get_table_names(
            database_url
        )
    )

    assert "users" not in (
        table_names_after_downgrade
    )
    assert "account_tokens" not in (
        table_names_after_downgrade
    )
    assert get_current_revision(
        database_url
    ) is None

    command.upgrade(
        alembic_config,
        "head",
    )

    final_table_names = get_table_names(
        database_url
    )

    assert "users" in final_table_names
    assert "account_tokens" in final_table_names

    assert get_current_revision(
        database_url
    ) == expected_head