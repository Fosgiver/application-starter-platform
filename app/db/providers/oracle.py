from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


ORACLE_PROVIDER_PROFILE = (
    DatabaseProviderProfile(
        provider_id=(
            DatabaseProviderId.ORACLE
        ),
        display_name="Oracle Database",
        sqlalchemy_dialect="oracle",
        sqlalchemy_driver="oracledb",
        database_url_example=(
            "oracle+oracledb://"
            "user:password@localhost:1521"
            "?service_name=application"
        ),
        driver_distribution=(
            "oracledb==4.0.2"
        ),
        default_port=1521,
        is_file_based=False,
    )
)