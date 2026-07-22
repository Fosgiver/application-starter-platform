import pytest

from app.db.providers import (
    DatabaseProviderId,
    POSTGRESQL_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_postgresql_provider_profile_is_complete(
) -> None:
    assert (
        POSTGRESQL_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.POSTGRESQL
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE.display_name
        == "PostgreSQL"
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE
        .sqlalchemy_dialect
        == "postgresql"
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE
        .sqlalchemy_driver
        == "psycopg"
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE
        .sqlalchemy_url_scheme
        == "postgresql+psycopg"
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE
        .driver_distribution
        == "psycopg[binary]==3.3.4"
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE.default_port
        == 5432
    )
    assert (
        POSTGRESQL_PROVIDER_PROFILE.is_file_based
        is False
    )


def test_postgresql_provider_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.POSTGRESQL
    )

    assert (
        profile
        is POSTGRESQL_PROVIDER_PROFILE
    )


def test_postgresql_accepts_locked_driver_url() -> None:
    database_url = (
        POSTGRESQL_PROVIDER_PROFILE
        .validate_database_url(
            "postgresql+psycopg://"
            "user:password@localhost:5432/database"
        )
    )

    assert (
        database_url.drivername
        == "postgresql+psycopg"
    )


def test_postgresql_rejects_implicit_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            POSTGRESQL_PROVIDER_PROFILE
            .validate_database_url(
                "postgresql://"
                "user:password@localhost/database"
            )
        )


def test_postgresql_rejects_psycopg2_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            POSTGRESQL_PROVIDER_PROFILE
            .validate_database_url(
                "postgresql+psycopg2://"
                "user:password@localhost/database"
            )
        )