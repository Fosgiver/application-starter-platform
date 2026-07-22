"""Application-specific API extension point."""

from fastapi import APIRouter

from app.core.manifest import (
    get_application_manifest,
)
from app.domain.schemas import (
    DomainStatusResponse,
)


router = APIRouter(
    prefix="/api",
    tags=["domain"],
)


@router.get(
    "/domain/status",
    response_model=DomainStatusResponse,
    summary="Check domain extension status",
)
def get_domain_status() -> DomainStatusResponse:
    manifest = get_application_manifest()

    return DomainStatusResponse(
        status="ready",
        application=manifest.application.name,
        version=manifest.application.version,
    )