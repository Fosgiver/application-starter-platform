from collections.abc import Iterable

from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)
from app.db.providers.mariadb import (
    MARIADB_PROVIDER_PROFILE,
)
from app.db.providers.mysql import (
    MYSQL_PROVIDER_PROFILE,
)
from app.db.providers.postgresql import (
    POSTGRESQL_PROVIDER_PROFILE,
)
from app.db.providers.sqlite import (
    SQLITE_PROVIDER_PROFILE,
)
from app.db.providers.sqlserver import (
    SQLSERVER_PROVIDER_PROFILE,
)

from app.db.providers.oracle import (
    ORACLE_PROVIDER_PROFILE,
)

def normalize_provider_id(
    provider_id: DatabaseProviderId | str,
) -> str:
    return str(provider_id).strip().lower()


class DatabaseProviderRegistry:
    def __init__(
        self,
        profiles: Iterable[
            DatabaseProviderProfile
        ] = (),
    ) -> None:
        self._profiles: dict[
            str,
            DatabaseProviderProfile,
        ] = {}

        for profile in profiles:
            self.register(profile)

    def register(
        self,
        profile: DatabaseProviderProfile,
    ) -> None:
        provider_id = normalize_provider_id(
            profile.provider_id
        )

        if provider_id in self._profiles:
            raise ValueError(
                "Database provider is already "
                f"registered: {provider_id}"
            )

        self._profiles[provider_id] = profile

    def get(
        self,
        provider_id: DatabaseProviderId | str,
    ) -> DatabaseProviderProfile:
        normalized_provider_id = (
            normalize_provider_id(
                provider_id
            )
        )

        try:
            return self._profiles[
                normalized_provider_id
            ]
        except KeyError as error:
            raise LookupError(
                "Database provider is not "
                "registered: "
                f"{normalized_provider_id}"
            ) from error


_BUILT_IN_PROVIDER_REGISTRY = (
    DatabaseProviderRegistry(
        profiles=[
            SQLITE_PROVIDER_PROFILE,
            POSTGRESQL_PROVIDER_PROFILE,
            MYSQL_PROVIDER_PROFILE,
            MARIADB_PROVIDER_PROFILE,
            SQLSERVER_PROVIDER_PROFILE,
            ORACLE_PROVIDER_PROFILE,
        ]
    )
)


def get_database_provider_profile(
    provider_id: DatabaseProviderId | str,
) -> DatabaseProviderProfile:
    return _BUILT_IN_PROVIDER_REGISTRY.get(
        provider_id
    )