import pytest
from sqlalchemy import text

from app.db.engine_factory import (
    create_database_engine,
)
from app.db.providers import DatabaseProviderId


def test_sqlite_runtime_engine_is_configured() -> None:
    engine = create_database_engine(
        database_url="sqlite:///:memory:",
        provider_id=DatabaseProviderId.SQLITE,
        echo=False,
    )

    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT 1")
                ).scalar_one()
                == 1
            )

            assert (
                connection.execute(
                    text(
                        "PRAGMA foreign_keys"
                    )
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_runtime_rejects_provider_url_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match="does not match provider",
    ):
        create_database_engine(
            database_url=(
                "postgresql+psycopg://"
                "user:password@localhost/database"
            ),
            provider_id=DatabaseProviderId.SQLITE,
            echo=False,
        )


def test_runtime_rejects_unregistered_provider() -> None:
    with pytest.raises(
        LookupError,
        match="not registered",
    ):
        create_database_engine(
            database_url="unknown://localhost/database",
            provider_id="unknown-provider",
            echo=False,
        )