from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.jwt_tokens import decode_access_token
from app.db.database import Base, get_db
from app.main import app
from app.models import User
from app.services.accounts import register_user


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_login_flow(monkeypatch) -> None:
    test_engine = create_test_engine()

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        user_id = user.id

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    verification_email_user_ids = []

    def record_verification_email(
        database_session,
        user,
    ) -> None:
        verification_email_user_ids.append(user.id)

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        "app.api.auth.send_email_verification",
        record_verification_email,
    )

    client = TestClient(app)

    try:
        wrong_password_response = client.post(
            "/login",
            json={
                "email": "user@example.com",
                "password": "WrongPassword!123",
            },
        )

        assert wrong_password_response.status_code == 401
        assert verification_email_user_ids == []

        unverified_response = client.post(
            "/login",
            json={
                "email": "user@example.com",
                "password": "StrongTestPassword!123",
            },
        )

        assert unverified_response.status_code == 403
        assert verification_email_user_ids == [user_id]

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None

            stored_user.is_email_verified = True
            database_session.commit()

        successful_response = client.post(
            "/login",
            json={
                "email": "USER@example.com",
                "password": "StrongTestPassword!123",
            },
        )

        assert successful_response.status_code == 200

        response_data = successful_response.json()

        assert response_data["success"] is True
        assert response_data["token_type"] == "bearer"
        assert response_data["expires_in"] > 0
        assert (
            decode_access_token(
                response_data["access_token"]
            )
            == user_id
        )

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None

            stored_user.is_active = False
            database_session.commit()

        inactive_response = client.post(
            "/login",
            json={
                "email": "user@example.com",
                "password": "StrongTestPassword!123",
            },
        )

        assert inactive_response.status_code == 403
        assert verification_email_user_ids == [user_id]

    finally:
        app.dependency_overrides.clear()