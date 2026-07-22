from dataclasses import FrozenInstanceError

import pytest
from sqlalchemy import (
    create_engine,
    text,
)

from app.db.providers import (
    DatabaseProviderId,
    DatabaseProviderProfile,
    DatabaseProviderRegistry,
    SQLITE_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_all_built_in_provider_ids_are_declared() -> None:
    assert set(DatabaseProviderId) == {
        DatabaseProviderId.SQLITE,
        DatabaseProviderId.POSTGRESQL,
        DatabaseProviderId.MYSQL,
        DatabaseProviderId.MARIADB,
        DatabaseProviderId.SQL_SERVER,
        DatabaseProviderId.ORACLE,
    }


def test_sqlite_provider_profile_is_complete() -> None:
    assert (
        SQLITE_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.SQLITE
    )
    assert (
        SQLITE_PROVIDER_PROFILE.display_name
        == "SQLite"
    )
    assert (
        SQLITE_PROVIDER_PROFILE.sqlalchemy_dialect
        == "sqlite"
    )
    assert (
        SQLITE_PROVIDER_PROFILE.sqlalchemy_driver
        == "pysqlite"
    )
    assert (
        SQLITE_PROVIDER_PROFILE.sqlalchemy_url_scheme
        == "sqlite+pysqlite"
    )
    assert (
        SQLITE_PROVIDER_PROFILE.driver_distribution
        is None
    )
    assert SQLITE_PROVIDER_PROFILE.default_port is None
    assert SQLITE_PROVIDER_PROFILE.is_file_based is True


def test_sqlite_provider_profile_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.SQLITE
    )

    assert profile is SQLITE_PROVIDER_PROFILE


def test_provider_profile_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        SQLITE_PROVIDER_PROFILE.display_name = (
            "Changed SQLite"
        )


def test_custom_provider_can_use_the_contract() -> None:
    profile = DatabaseProviderProfile(
        provider_id="exampledb",
        display_name="Example Database",
        sqlalchemy_dialect="example",
        sqlalchemy_driver="exampledriver",
        database_url_example=(
            "example+exampledriver://"
            "user:password@localhost:1234/"
            "application"
        ),
        driver_distribution="example-driver",
        default_port=1234,
        is_file_based=False,
    )

    registry = DatabaseProviderRegistry()
    registry.register(profile)

    assert registry.get("exampledb") is profile


def test_duplicate_provider_registration_is_rejected() -> None:
    registry = DatabaseProviderRegistry(
        profiles=[
            SQLITE_PROVIDER_PROFILE,
        ]
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            SQLITE_PROVIDER_PROFILE
        )


def test_unknown_provider_is_rejected() -> None:
    registry = DatabaseProviderRegistry()

    with pytest.raises(
        LookupError,
        match="not registered",
    ):
        registry.get("unknown-provider")


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///:memory:",
        "sqlite+pysqlite:///:memory:",
    ],
)
def test_sqlite_accepts_supported_url_schemes(
    database_url: str,
) -> None:
    validated_url = (
        SQLITE_PROVIDER_PROFILE
        .validate_database_url(
            database_url
        )
    )

    assert validated_url.drivername in {
        "sqlite",
        "sqlite+pysqlite",
    }


def test_sqlite_rejects_another_database_dialect() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            SQLITE_PROVIDER_PROFILE
            .validate_database_url(
                "postgresql+psycopg://"
                "user:password@localhost/database"
            )
        )


def test_sqlite_rejects_an_unapproved_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            SQLITE_PROVIDER_PROFILE
            .validate_database_url(
                "sqlite+aiosqlite:///:memory:"
            )
        )


def test_sqlite_supplies_required_engine_options() -> None:
    database_url = (
        SQLITE_PROVIDER_PROFILE
        .validate_database_url(
            "sqlite:///:memory:"
        )
    )

    engine_options = (
        SQLITE_PROVIDER_PROFILE
        .get_engine_options(
            database_url
        )
    )

    assert engine_options == {
        "connect_args": {
            "check_same_thread": False,
        },
    }


def test_sqlite_enables_foreign_keys() -> None:
    database_url = (
        SQLITE_PROVIDER_PROFILE
        .validate_database_url(
            "sqlite:///:memory:"
        )
    )

    engine = create_engine(
        database_url,
        **(
            SQLITE_PROVIDER_PROFILE
            .get_engine_options(
                database_url
            )
        ),
    )

    SQLITE_PROVIDER_PROFILE.configure_engine(
        engine
    )

    try:
        with engine.connect() as connection:
            foreign_keys_enabled = (
                connection.execute(
                    text(
                        "PRAGMA foreign_keys"
                    )
                ).scalar_one()
            )

        assert foreign_keys_enabled == 1
    finally:
        engine.dispose()

@pytest.mark.parametrize(
    (
        "provider_id",
        "expected_database_url_example",
    ),
    [
        (
            DatabaseProviderId.SQLITE,
            "sqlite:///./"
            "application_starter_platform.db",
        ),
        (
            DatabaseProviderId.POSTGRESQL,
            "postgresql+psycopg://"
            "user:password@localhost:5432/"
            "application",
        ),
        (
            DatabaseProviderId.MYSQL,
            "mysql+pymysql://"
            "user:password@localhost:3306/"
            "application?charset=utf8mb4",
        ),
        (
            DatabaseProviderId.MARIADB,
            "mariadb+pymysql://"
            "user:password@localhost:3306/"
            "application?charset=utf8mb4",
        ),
        (
            DatabaseProviderId.SQL_SERVER,
            "mssql+pymssql://"
            "user:password@localhost:1433/"
            "application?charset=utf8",
        ),
        (
            DatabaseProviderId.ORACLE,
            "oracle+oracledb://"
            "user:password@localhost:1521"
            "?service_name=application",
        ),
    ],
)
def test_built_in_provider_database_url_example(
    provider_id: DatabaseProviderId,
    expected_database_url_example: str,
) -> None:
    profile = get_database_provider_profile(
        provider_id
    )

    assert (
        profile.database_url_example
        == expected_database_url_example
    )

    parsed_url = profile.validate_database_url(
        profile.database_url_example
    )

    assert (
        parsed_url.drivername
        in profile.accepted_database_url_schemes
    )