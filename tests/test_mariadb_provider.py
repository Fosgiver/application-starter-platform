import pytest

from app.db.providers import (
    DatabaseProviderId,
    MARIADB_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_mariadb_provider_profile_is_complete(
) -> None:
    assert (
        MARIADB_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.MARIADB
    )
    assert (
        MARIADB_PROVIDER_PROFILE.display_name
        == "MariaDB"
    )
    assert (
        MARIADB_PROVIDER_PROFILE
        .sqlalchemy_dialect
        == "mariadb"
    )
    assert (
        MARIADB_PROVIDER_PROFILE
        .sqlalchemy_driver
        == "pymysql"
    )
    assert (
        MARIADB_PROVIDER_PROFILE
        .sqlalchemy_url_scheme
        == "mariadb+pymysql"
    )
    assert (
        MARIADB_PROVIDER_PROFILE
        .driver_distribution
        == "PyMySQL[ed25519,rsa]==1.2.0"
    )
    assert (
        MARIADB_PROVIDER_PROFILE.default_port
        == 3306
    )
    assert (
        MARIADB_PROVIDER_PROFILE.is_file_based
        is False
    )


def test_mariadb_provider_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.MARIADB
    )

    assert profile is MARIADB_PROVIDER_PROFILE


def test_mariadb_accepts_locked_driver_url() -> None:
    database_url = (
        MARIADB_PROVIDER_PROFILE
        .validate_database_url(
            "mariadb+pymysql://"
            "user:password@localhost:3306/database"
            "?charset=utf8mb4"
        )
    )

    assert (
        database_url.drivername
        == "mariadb+pymysql"
    )
    assert (
        database_url.query["charset"]
        == "utf8mb4"
    )


def test_mariadb_rejects_implicit_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            MARIADB_PROVIDER_PROFILE
            .validate_database_url(
                "mariadb://"
                "user:password@localhost/database"
            )
        )


def test_mariadb_rejects_mysql_dialect() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            MARIADB_PROVIDER_PROFILE
            .validate_database_url(
                "mysql+pymysql://"
                "user:password@localhost/database"
            )
        )