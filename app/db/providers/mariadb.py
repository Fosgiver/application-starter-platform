from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


MARIADB_PROVIDER_PROFILE = (
    DatabaseProviderProfile(
        provider_id=DatabaseProviderId.MARIADB,
        display_name="MariaDB",
        sqlalchemy_dialect="mariadb",
        sqlalchemy_driver="pymysql",
        database_url_example=(
            "mariadb+pymysql://"
            "user:password@localhost:3306/"
            "application?charset=utf8mb4"
        ),
        driver_distribution=(
            "PyMySQL[ed25519,rsa]==1.2.0"
        ),
        default_port=3306,
        is_file_based=False,
    )
)