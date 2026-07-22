from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models import (
    AccountToken,
    AccountTokenPurpose,
)
from app.services.accounts import register_user

from app.models import (
    AccountToken,
    AccountTokenPurpose,
    User,
)

def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_forgot_password_endpoint_is_neutral_and_issues_token(
    monkeypatch,
) -> None:
    test_engine = create_test_engine()

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    def skip_email_delivery(*args, **kwargs) -> None:
        return None

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        "app.services.password_reset.send_email",
        skip_email_delivery,
    )

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        user_id = user.id

        assert user.is_email_verified is False

    client = TestClient(app)

    expected_response = {
        "success": True,
        "message": (
            "If the account can continue, "
            "the appropriate instructions will be sent."
        ),
    }

    try:
        existing_account_response = client.post(
            "/password/forgot",
            json={
                "email": "USER@example.com",
            },
        )

        assert existing_account_response.status_code == 202
        assert existing_account_response.json() == expected_response

        with Session(test_engine) as database_session:
            stored_tokens = database_session.scalars(
                select(AccountToken).where(
                    AccountToken.user_id == user_id,
                    AccountToken.purpose
                    == AccountTokenPurpose.PASSWORD_RESET.value,
                )
            ).all()

            assert len(stored_tokens) == 1

            stored_token = stored_tokens[0]

            assert stored_token.used_at is None
            assert stored_token.revoked_at is None

            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None
            assert stored_user.is_email_verified is False

        unknown_account_response = client.post(
            "/password/forgot",
            json={
                "email": "unknown@example.com",
            },
        )

        assert unknown_account_response.status_code == 202
        assert unknown_account_response.json() == expected_response

        with Session(test_engine) as database_session:
            stored_tokens = database_session.scalars(
                select(AccountToken).where(
                    AccountToken.purpose
                    == AccountTokenPurpose.PASSWORD_RESET.value,
                )
            ).all()

            assert len(stored_tokens) == 1

    finally:
        app.dependency_overrides.clear()