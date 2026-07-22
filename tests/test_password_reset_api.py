from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.one_time_tokens import hash_one_time_token
from app.auth.passwords import verify_password
from app.db.database import Base, get_db
from app.main import app
from app.models import (
    AccountToken,
    AccountTokenPurpose,
    User,
)
from app.services.account_tokens import (
    issue_account_token,
    utc_now,
)
from app.services.accounts import register_user


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_password_reset_changes_password_and_verifies_email() -> None:
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
        original_is_active = user.is_active
       
        assert user.is_email_verified is False
        assert user.email_verified_at is None

        raw_token = issue_account_token(
            database_session,
            user_id=user_id,
            purpose=AccountTokenPurpose.PASSWORD_RESET,
            lifetime_minutes=30,
        )

    client = TestClient(app)

    try:
        response = client.post(
            "/password/reset",
            json={
                "token": raw_token,
                "new_password": new_password,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": (
                "Password reset completed successfully."
            ),
        }

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None

            assert verify_password(
                new_password,
                stored_user.password_hash,
            )

            assert not verify_password(
                old_password,
                stored_user.password_hash,
            )

            assert (
                stored_user.is_active
                == original_is_active
            )
            assert stored_user.is_email_verified is True
            assert stored_user.email_verified_at is not None
  

            stored_token = database_session.scalar(
                select(AccountToken).where(
                    AccountToken.token_hash
                    == hash_one_time_token(raw_token),
                )
            )

            assert stored_token is not None
            assert stored_token.used_at is not None
            assert stored_token.revoked_at is None

        reused_token_response = client.post(
            "/password/reset",
            json={
                "token": raw_token,
                "new_password": "AnotherStrongPassword!789",
            },
        )

        assert reused_token_response.status_code == 400
        assert reused_token_response.json() == {
            "success": False,
            "message": (
                "Password reset token is invalid or expired."
            ),
        }

        invalid_token_response = client.post(
            "/password/reset",
            json={
                "token": "invalid-password-reset-token",
                "new_password": "AnotherStrongPassword!789",
            },
        )

        assert invalid_token_response.status_code == 400
        assert invalid_token_response.json() == {
            "success": False,
            "message": (
                "Password reset token is invalid or expired."
            ),
        }

    finally:
        app.dependency_overrides.clear()


def test_password_reset_preserves_existing_email_verification() -> None:
    test_engine = create_test_engine()

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db

    new_password = "NewStrongPassword!456"

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="verified@example.com",
            plain_password="StrongTestPassword!123",
        )

        user.is_email_verified = True
        user.email_verified_at = utc_now()

        database_session.commit()
        database_session.refresh(user)

        user_id = user.id
        original_email_verified_at = (
            user.email_verified_at
        )

        raw_token = issue_account_token(
            database_session,
            user_id=user_id,
            purpose=AccountTokenPurpose.PASSWORD_RESET,
            lifetime_minutes=30,
        )

    client = TestClient(app)

    try:
        response = client.post(
            "/password/reset",
            json={
                "token": raw_token,
                "new_password": new_password,
            },
        )

        assert response.status_code == 200

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None
            assert stored_user.is_email_verified is True
            assert (
                stored_user.email_verified_at
                == original_email_verified_at
            )

            assert verify_password(
                new_password,
                stored_user.password_hash,
            )

    finally:
        app.dependency_overrides.clear()