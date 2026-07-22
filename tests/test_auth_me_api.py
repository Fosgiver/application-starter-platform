from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.jwt_tokens import create_access_token
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


def test_auth_me_endpoint() -> None:
    test_engine = create_test_engine()

    with Session(test_engine) as database_session:
        user = register_user(
            database_session,
            email="user@example.com",
            plain_password="StrongTestPassword!123",
        )

        user.is_email_verified = True
        database_session.commit()

        user_id = user.id

    access_token = create_access_token(user_id)

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    try:
        missing_token_response = client.get(
            "/auth/me"
        )

        assert missing_token_response.status_code == 401
        assert (
            missing_token_response.headers["www-authenticate"]
            == "Bearer"
        )

        invalid_token_response = client.get(
            "/auth/me",
            headers={
                "Authorization": "Bearer invalid-token"
            },
        )

        assert invalid_token_response.status_code == 401

        successful_response = client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
        )

        assert successful_response.status_code == 200

        response_data = successful_response.json()

        assert response_data["success"] is True
        assert (
            response_data["account"]["account_id"]
            == str(user_id)
        )
        assert (
            response_data["account"]["email"]
            == "user@example.com"
        )
        assert (
            response_data["account"]["email_verified"]
            is True
        )

        with Session(test_engine) as database_session:
            stored_user = database_session.get(
                User,
                user_id,
            )

            assert stored_user is not None

            stored_user.is_active = False
            database_session.commit()

        inactive_user_response = client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
        )

        assert inactive_user_response.status_code == 401

    finally:
        app.dependency_overrides.clear()