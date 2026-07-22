import pytest

from app.db.providers import (
    DatabaseProviderId,
    MYSQL_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_mysql_provider_profile_is_complete(
) -> None:
    assert (
        MYSQL_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.MYSQL
    )
    assert (
        MYSQL_PROVIDER_PROFILE.display_name
        == "MySQL"
    )
    assert (
        MYSQL_PROVIDER_PROFILE
        .sqlalchemy_dialect
        == "mysql"
    )
    assert (
        MYSQL_PROVIDER_PROFILE
        .sqlalchemy_driver
        == "pymysql"
    )
    assert (
        MYSQL_PROVIDER_PROFILE
        .sqlalchemy_url_scheme
        == "mysql+pymysql"
    )
    assert (
        MYSQL_PROVIDER_PROFILE
        .driver_distribution
        == "PyMySQL[rsa]==1.2.0"
    )
    assert (
        MYSQL_PROVIDER_PROFILE.default_port
        == 3306
    )
    assert (
        MYSQL_PROVIDER_PROFILE.is_file_based
        is False
    )


def test_mysql_provider_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.MYSQL
    )

    assert profile is MYSQL_PROVIDER_PROFILE


def test_mysql_accepts_locked_driver_url() -> None:
    database_url = (
        MYSQL_PROVIDER_PROFILE
        .validate_database_url(
            "mysql+pymysql://"
            "user:password@localhost:3306/database"
            "?charset=utf8mb4"
        )
    )

    assert (
        database_url.drivername
        == "mysql+pymysql"
    )
    assert (
        database_url.query["charset"]
        == "utf8mb4"
    )


def test_mysql_rejects_implicit_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            MYSQL_PROVIDER_PROFILE
            .validate_database_url(
                "mysql://"
                "user:password@localhost/database"
            )
        )


def test_mysql_rejects_mysqldb_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            MYSQL_PROVIDER_PROFILE
            .validate_database_url(
                "mysql+mysqldb://"
                "user:password@localhost/database"
            )
        )