from app.db.providers.base import (
    DatabaseProviderId,
    DatabaseProviderProfile,
)


MYSQL_PROVIDER_PROFILE = (
    DatabaseProviderProfile(
        provider_id=DatabaseProviderId.MYSQL,
        display_name="MySQL",
        sqlalchemy_dialect="mysql",
        sqlalchemy_driver="pymysql",
        database_url_example=(
            "mysql+pymysql://"
            "user:password@localhost:3306/"
            "application?charset=utf8mb4"
        ),
        driver_distribution=(
            "PyMySQL[rsa]==1.2.0"
        ),
        default_port=3306,
        is_file_based=False,
    )
)