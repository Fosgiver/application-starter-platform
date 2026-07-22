import pytest

from app.db.providers import (
    DatabaseProviderId,
    ORACLE_PROVIDER_PROFILE,
    get_database_provider_profile,
)


def test_oracle_provider_profile_is_complete(
) -> None:
    assert (
        ORACLE_PROVIDER_PROFILE.provider_id
        == DatabaseProviderId.ORACLE
    )
    assert (
        ORACLE_PROVIDER_PROFILE.display_name
        == "Oracle Database"
    )
    assert (
        ORACLE_PROVIDER_PROFILE
        .sqlalchemy_dialect
        == "oracle"
    )
    assert (
        ORACLE_PROVIDER_PROFILE
        .sqlalchemy_driver
        == "oracledb"
    )
    assert (
        ORACLE_PROVIDER_PROFILE
        .sqlalchemy_url_scheme
        == "oracle+oracledb"
    )
    assert (
        ORACLE_PROVIDER_PROFILE
        .driver_distribution
        == "oracledb==4.0.2"
    )
    assert (
        ORACLE_PROVIDER_PROFILE.default_port
        == 1521
    )
    assert (
        ORACLE_PROVIDER_PROFILE.is_file_based
        is False
    )


def test_oracle_provider_is_registered() -> None:
    profile = get_database_provider_profile(
        DatabaseProviderId.ORACLE
    )

    assert profile is ORACLE_PROVIDER_PROFILE


def test_oracle_accepts_locked_driver_url() -> None:
    database_url = (
        ORACLE_PROVIDER_PROFILE
        .validate_database_url(
            "oracle+oracledb://"
            "user:password@localhost:1521"
            "?service_name=freepdb1"
        )
    )

    assert (
        database_url.drivername
        == "oracle+oracledb"
    )
    assert (
        database_url.query["service_name"]
        == "freepdb1"
    )


def test_oracle_rejects_implicit_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            ORACLE_PROVIDER_PROFILE
            .validate_database_url(
                "oracle://"
                "user:password@localhost:1521"
                "?service_name=freepdb1"
            )
        )


def test_oracle_rejects_obsolete_driver() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        (
            ORACLE_PROVIDER_PROFILE
            .validate_database_url(
                "oracle+cx_oracle://"
                "user:password@localhost:1521"
                "?service_name=freepdb1"
            )
        )