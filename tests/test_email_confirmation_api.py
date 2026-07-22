from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models import AccountTokenPurpose, User
from app.services.account_tokens import issue_account_token
from app.services.accounts import register_user


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_email_confirmation_endpoint() -> None:
    test_engine = create_test_engine()

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        user_id = user.id

        raw_token = issue_account_token(
            database_session,
            user_id=user_id,
            purpose=AccountTokenPurpose.EMAIL_VERIFICATION,
            lifetime_minutes=30,
        )

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    try:
        response = client.post(
            "/email-verification/confirm",
            json={"token": raw_token},
        )

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Email address verified successfully.",
        }

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None
            assert stored_user.is_email_verified is True
            assert stored_user.email_verified_at is not None

        repeated_response = client.post(
            "/email-verification/confirm",
            json={"token": raw_token},
        )

        assert repeated_response.status_code == 409

        invalid_response = client.post(
            "/email-verification/confirm",
            json={"token": "invalid-token"},
        )

        assert invalid_response.status_code == 400

    finally:
        app.dependency_overrides.clear()