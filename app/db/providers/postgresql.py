from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


POSTGRESQL_PROVIDER_PROFILE = (
    DatabaseProviderProfile(
        provider_id=(
            DatabaseProviderId.POSTGRESQL
        ),
        display_name="PostgreSQL",
        sqlalchemy_dialect="postgresql",
        sqlalchemy_driver="psycopg",
        database_url_example=(
            "postgresql+psycopg://"
            "user:password@localhost:5432/"
            "application"
        ),
        driver_distribution=(
            "psycopg[binary]==3.3.4"
        ),
        default_port=5432,
        is_file_based=False,
    )
)