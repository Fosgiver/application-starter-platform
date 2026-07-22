from app.core.paths import get_frontend_directory

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.auth.dependencies import AuthenticationRequiredError
from app.core.settings import settings
from app.domain import router as domain_router


FRONTEND_DIRECTORY = get_frontend_directory()


async def authentication_required_handler(
    _request: Request,
    _error: AuthenticationRequiredError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "success": False,
            "message": "Authentication is required.",
        },
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )


def create_app() -> FastAPI:
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = (
        "/openapi.json"
        if settings.docs_enabled
        else None
    )

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    application.add_exception_handler(
        AuthenticationRequiredError,
        authentication_required_handler,
    )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(domain_router)
    
    application.mount(
        "/",
        StaticFiles(
            directory=FRONTEND_DIRECTORY,
            html=True,
        ),
        name="frontend",
    )

    return application


app = create_app()