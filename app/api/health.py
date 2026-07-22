from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings import settings


router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    application: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check application health",
    operation_id="getHealth",
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        application=settings.app_name,
        version=settings.app_version,
    )