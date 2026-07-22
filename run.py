import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from app.core.paths import is_bundled_application
from app.core.settings import settings
from app.db.migration_runner import (
    run_database_migrations,
)


def get_application_url() -> str:
    browser_host = settings.api_host

    if browser_host in {"0.0.0.0", "::"}:
        browser_host = "127.0.0.1"

    return (
        f"http://{browser_host}:"
        f"{settings.api_port}/"
    )


def open_browser_when_ready() -> None:
    application_url = get_application_url()
    health_url = f"{application_url}health"

    for _attempt in range(60):
        try:
            with urllib.request.urlopen(
                health_url,
                timeout=1,
            ):
                webbrowser.open(application_url)
                return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)


def start_browser_thread() -> None:
    if not is_bundled_application():
        return

    if not settings.open_browser_on_start:
        return

    browser_thread = threading.Thread(
        target=open_browser_when_ready,
        name="browser-launcher",
        daemon=True,
    )
    browser_thread.start()


def main() -> None:
    run_database_migrations()
    start_browser_thread()

    development_reload = (
        settings.environment == "development"
        and not is_bundled_application()
    )

    if development_reload:
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True,
        )
        return

    from app.main import app

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()