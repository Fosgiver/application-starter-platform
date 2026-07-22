import pytest

from app.db.providers import (
    DatabaseProviderId,
    SQLSERVER_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_sqlserver_provider_profile_is_complete(
) -> None:
    assert (
        SQLSERVER_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.SQL_SERVER
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE.display_name
        == "Microsoft SQL Server"
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE
        .sqlalchemy_dialect
        == "mssql"
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE
        .sqlalchemy_driver
        == "pymssql"
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE
        .sqlalchemy_url_scheme
        == "mssql+pymssql"
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE
        .driver_distribution
        == "pymssql==2.3.13"
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE.default_port
        == 1433
    )
    assert (
        SQLSERVER_PROVIDER_PROFILE.is_file_based
        is False
    )


def test_sqlserver_provider_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.SQL_SERVER
    )

    assert profile is SQLSERVER_PROVIDER_PROFILE


def test_sqlserver_accepts_locked_driver_url() -> None:
    database_url = (
        SQLSERVER_PROVIDER_PROFILE
        .validate_database_url(
            "mssql+pymssql://"
            "user:password@localhost:1433/database"
            "?charset=utf8"
        )
    )

    assert (
        database_url.drivername
        == "mssql+pymssql"
    )
    assert (
        database_url.query["charset"]
        == "utf8"
    )


def test_sqlserver_rejects_implicit_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            SQLSERVER_PROVIDER_PROFILE
            .validate_database_url(
                "mssql://"
                "user:password@localhost/database"
            )
        )


def test_sqlserver_rejects_pyodbc_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            SQLSERVER_PROVIDER_PROFILE
            .validate_database_url(
                "mssql+pyodbc://"
                "user:password@localhost/database"
            )
        )