from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models import (
    AccountToken,
    AccountTokenPurpose,
    User,
)
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


def test_manual_login_after_password_reset_succeeds() -> None:
    test_engine = create_test_engine()

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db

    old_password = "StrongTestPassword!123"
    new_password = "NewStrongPassword!456"

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password=old_password,
        )

        user_id = user.id

        reset_token = issue_account_token(
            database_session,
            user_id=user_id,
            purpose=AccountTokenPurpose.PASSWORD_RESET,
            lifetime_minutes=30,
        )

    client = TestClient(app)

    try:
        reset_response = client.post(
            "/password/reset",
            json={
                "token": reset_token,
                "new_password": new_password,
            },
        )

        assert reset_response.status_code == 200
        assert reset_response.json() == {
            "success": True,
            "message": (
                "Password reset completed successfully."
            ),
        }

        assert "access_token" not in reset_response.json()

        old_password_login = client.post(
            "/login",
            json={
                "email": "user@example.com",
                "password": old_password,
            },
        )

        assert old_password_login.status_code == 401
        assert old_password_login.json() == {
            "success": False,
            "message": "Invalid email address or password.",
        }

        new_password_login = client.post(
            "/login",
            json={
                "email": "user@example.com",
                "password": new_password,
            },
        )

        assert new_password_login.status_code == 200

        login_data = new_password_login.json()

        assert login_data["success"] is True
        assert isinstance(login_data["access_token"], str)
        assert login_data["access_token"]
        assert login_data["token_type"] == "bearer"
        assert login_data["expires_in"] > 0

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None
            assert stored_user.is_active is True
            assert stored_user.is_email_verified is True
            assert stored_user.email_verified_at is not None

            verification_tokens = database_session.scalars(
                select(AccountToken).where(
                    AccountToken.user_id == user_id,
                    AccountToken.purpose
                    == AccountTokenPurpose.EMAIL_VERIFICATION.value,
                )
            ).all()

            assert verification_tokens == []

    finally:
        app.dependency_overrides.clear()