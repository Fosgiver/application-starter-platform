from pathlib import Path

import yaml

from app.main import app


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "application_starter_platform.yaml"


def main() -> None:
    openapi_content = yaml.safe_dump(
        app.openapi(),
        sort_keys=False,
        allow_unicode=True,
    )

    OUTPUT_PATH.write_text(
        openapi_content,
        encoding="utf-8",
    )

    print(
        f"OpenAPI schema exported to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()