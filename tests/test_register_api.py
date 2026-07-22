from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.passwords import verify_password
from app.db.database import Base, get_db
from app.main import app
from app.models import User


def create_test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    return engine


def test_register_endpoint(monkeypatch) -> None:
    test_engine = create_test_engine()

    def override_get_db():
        with Session(test_engine) as database_session:
            yield database_session

    def skip_verification_email(*args, **kwargs) -> None:
        return None

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        "app.api.auth.send_email_verification",
        skip_verification_email,
    )

    client = TestClient(app)

    try:
        response = client.post(
            "/register",
            json={
                "email": "User@Example.com",
                "password": "StrongTestPassword!123",
            },
        )

        assert response.status_code == 201
        assert response.json()["success"] is True

        with Session(test_engine) as database_session:
            stored_user = database_session.scalar(
                select(User).where(
                    User.email == "user@example.com"
                )
            )

            assert stored_user is not None
            assert stored_user.password_hash != (
                "StrongTestPassword!123"
            )
            assert verify_password(
                "StrongTestPassword!123",
                stored_user.password_hash,
            )

        duplicate_response = client.post(
            "/register",
            json={
                "email": "USER@example.com",
                "password": "AnotherPassword!123",
            },
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {
            "success": False,
            "message": "Email address is already registered.",
        }

    finally:
        app.dependency_overrides.clear()