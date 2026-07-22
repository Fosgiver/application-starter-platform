from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
    }