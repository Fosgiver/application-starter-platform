import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.passwords import verify_password
from app.db.database import Base
from app.services.accounts import (
    EmailAlreadyRegisteredError,
    get_user_by_email,
    register_user,
)


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_register_user() -> None:
    engine = create_test_engine()

    with Session(engine) as database_session:
        user = register_user(
            database_session,
            email="User@Example.com",
            plain_password="StrongTestPassword!123",
        )

        assert user.email == "user@example.com"
        assert user.password_hash != "StrongTestPassword!123"
        assert verify_password(
            "StrongTestPassword!123",
            user.password_hash,
        )

        stored_user = get_user_by_email(
            database_session,
            "USER@example.com",
        )

        assert stored_user is not None
        assert stored_user.id == user.id


def test_duplicate_email_is_rejected() -> None:
    engine = create_test_engine()

    with Session(engine) as database_session:
        register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        with pytest.raises(EmailAlreadyRegisteredError):
            register_user(
                database_session,
                email="USER@example.com",
                plain_password="AnotherPassword!123",
            )