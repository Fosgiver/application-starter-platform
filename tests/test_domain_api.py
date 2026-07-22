from fastapi.testclient import TestClient

from app.core.manifest import (
    get_application_manifest,
)
from app.main import app


client = TestClient(app)


def test_domain_status_endpoint() -> None:
    manifest = get_application_manifest()

    response = client.get(
        "/api/domain/status"
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "application": manifest.application.name,
        "version": manifest.application.version,
    }