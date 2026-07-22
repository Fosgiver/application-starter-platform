from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import (
    Engine,
    URL,
)

from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


class SQLiteDatabaseProviderProfile(
    DatabaseProviderProfile
):
    def get_engine_options(
        self,
        database_url: URL,
    ) -> dict[str, Any]:
        return {
            "connect_args": {
                "check_same_thread": False,
            },
        }

    def configure_engine(
        self,
        engine: Engine,
    ) -> None:
        @event.listens_for(
            engine,
            "connect",
        )
        def enable_sqlite_foreign_keys(
            dbapi_connection: Any,
            _connection_record: Any,
        ) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute(
                "PRAGMA foreign_keys=ON"
            )
            cursor.close()


SQLITE_PROVIDER_PROFILE = (
    SQLiteDatabaseProviderProfile(
        provider_id=DatabaseProviderId.SQLITE,
        display_name="SQLite",
        sqlalchemy_dialect="sqlite",
        sqlalchemy_driver="pysqlite",
                database_url_example=(
            "sqlite:///./"
            "application_starter_platform.db"
        ),
        driver_distribution=None,
        default_port=None,
        is_file_based=True,
    )
)