from collections.abc import Generator

from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.core.manifest import (
    get_application_manifest,
)
from app.core.settings import settings
from app.db.base import Base
from app.db.engine_factory import (
    create_database_engine,
)


application_manifest = get_application_manifest()

engine = create_database_engine(
    database_url=settings.database_url,
    provider_id=(
        application_manifest.database.provider
    ),
    echo=settings.database_echo,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    database_session = SessionLocal()

    try:
        yield database_session
    finally:
        database_session.close()