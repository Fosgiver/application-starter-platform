from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any

from sqlalchemy.engine import (
    Engine,
    URL,
    make_url,
)
from sqlalchemy.exc import ArgumentError


_PROVIDER_ID_PATTERN = re.compile(
    r"^[a-z][a-z0-9_-]*$"
)

_SQLALCHEMY_NAME_PATTERN = re.compile(
    r"^[a-z][a-z0-9_]*$"
)


class DatabaseProviderId(StrEnum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MARIADB = "mariadb"
    SQL_SERVER = "sqlserver"
    ORACLE = "oracle"


@dataclass(
    frozen=True,
    slots=True,
)
class DatabaseProviderProfile:
    provider_id: DatabaseProviderId | str
    display_name: str
    sqlalchemy_dialect: str
    sqlalchemy_driver: str
    database_url_example: str
    driver_distribution: str | None
    default_port: int | None
    is_file_based: bool

    def __post_init__(self) -> None:
        provider_id = str(
            self.provider_id
        )

        if not _PROVIDER_ID_PATTERN.fullmatch(
            provider_id
        ):
            raise ValueError(
                "provider_id must contain only "
                "lowercase letters, numbers, "
                "underscores, or hyphens."
            )

        if not self.display_name.strip():
            raise ValueError(
                "display_name must not be empty."
            )

        if not _SQLALCHEMY_NAME_PATTERN.fullmatch(
            self.sqlalchemy_dialect
        ):
            raise ValueError(
                "sqlalchemy_dialect is invalid."
            )

        if not _SQLALCHEMY_NAME_PATTERN.fullmatch(
            self.sqlalchemy_driver
        ):
            raise ValueError(
                "sqlalchemy_driver is invalid."
            )

        if not self.database_url_example.strip():
            raise ValueError(
                "database_url_example must not "
                "be empty."
            )

        if (
            self.driver_distribution is not None
            and not self.driver_distribution.strip()
        ):
            raise ValueError(
                "driver_distribution must not "
                "be empty."
            )

        if (
            self.default_port is not None
            and not 1 <= self.default_port <= 65535
        ):
            raise ValueError(
                "default_port must be between "
                "1 and 65535."
            )

        self.validate_database_url(
            self.database_url_example
        )

    @property
    def sqlalchemy_url_scheme(self) -> str:
        return (
            f"{self.sqlalchemy_dialect}"
            f"+{self.sqlalchemy_driver}"
        )

    @property
    def accepted_database_url_schemes(
        self,
    ) -> tuple[str, ...]:
        explicit_scheme = (
            self.sqlalchemy_url_scheme
        )

        if self.driver_distribution is None:
            return (
                self.sqlalchemy_dialect,
                explicit_scheme,
            )

        return (
            explicit_scheme,
        )

    def validate_database_url(
        self,
        database_url: str | URL,
    ) -> URL:
        try:
            parsed_url = make_url(
                database_url
            )
        except (
            ArgumentError,
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                "Database URL is invalid."
            ) from error

        if (
            parsed_url.drivername.lower()
            not in self.accepted_database_url_schemes
        ):
            raise ValueError(
                "Database URL scheme "
                f"'{parsed_url.drivername}' "
                "does not match provider "
                f"'{self.provider_id}'."
            )

        return parsed_url

    def get_engine_options(
        self,
        database_url: URL,
    ) -> dict[str, Any]:
        return {}

    def configure_engine(
        self,
        engine: Engine,
    ) -> None:
        return None