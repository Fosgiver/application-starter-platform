from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


SQLSERVER_PROVIDER_PROFILE = (
    DatabaseProviderProfile(
        provider_id=(
            DatabaseProviderId.SQL_SERVER
        ),
        display_name="Microsoft SQL Server",
        sqlalchemy_dialect="mssql",
        sqlalchemy_driver="pymssql",
        database_url_example=(
            "mssql+pymssql://"
            "user:password@localhost:1433/"
            "application?charset=utf8"
        ),
        driver_distribution=(
            "pymssql==2.3.13"
        ),
        default_port=1433,
        is_file_based=False,
    )
)