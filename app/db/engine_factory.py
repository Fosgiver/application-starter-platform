from collections.abc import Mapping
from typing import Any

from sqlalchemy import (
    create_engine as create_sqlalchemy_engine,
)
from sqlalchemy.engine import (
    Engine,
    URL,
)

from app.db.providers import (
    DatabaseProviderId,
    get_database_provider_profile,
)


def create_database_engine(
    database_url: str | URL,
    provider_id: DatabaseProviderId | str,
    echo: bool = False,
    additional_engine_options: (
        Mapping[str, Any] | None
    ) = None,
) -> Engine:
    provider_profile = (
        get_database_provider_profile(
            provider_id
        )
    )

    validated_database_url = (
        provider_profile.validate_database_url(
            database_url
        )
    )

    engine_options = dict(
        provider_profile.get_engine_options(
            validated_database_url
        )
    )

    if additional_engine_options is not None:
        duplicate_options = (
            set(engine_options)
            & set(additional_engine_options)
        )

        if duplicate_options:
            duplicate_text = ", ".join(
                sorted(duplicate_options)
            )

            raise ValueError(
                "Engine options are already "
                "defined by the provider: "
                f"{duplicate_text}"
            )

        engine_options.update(
            additional_engine_options
        )

    database_engine = create_sqlalchemy_engine(
        validated_database_url,
        echo=echo,
        **engine_options,
    )

    provider_profile.configure_engine(
        database_engine
    )

    return database_engine