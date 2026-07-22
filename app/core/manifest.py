from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from app.core.paths import (
    get_application_manifest_path,
)
from app.db.providers import (
    DatabaseProviderId,
)


class ManifestSection(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class ApplicationSection(ManifestSection):
    name: str = Field(min_length=1)
    slug: str = Field(
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    version: str = Field(
        pattern=r"^\d+\.\d+\.\d+$"
    )
    publisher: str = Field(min_length=1)
    description: str = Field(min_length=1)


class RuntimeSection(ManifestSection):
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    open_browser_on_start: bool
    post_login_path: str = Field(
        pattern=r"^/"
    )


class DataSection(ManifestSection):
    directory_name: str = Field(min_length=1)


class DatabaseSection(ManifestSection):
    provider: DatabaseProviderId


class EmailSection(ManifestSection):
    mode: Literal[
        "gmail",
        "smtp",
        "console",
    ]

    from_name: str = Field(min_length=1)


class FeaturesSection(ManifestSection):
    self_registration: bool
    email_verification: bool
    password_reset: bool


class DevelopmentSection(ManifestSection):
    domain_package: str = Field(
        pattern=(
            r"^[A-Za-z_][A-Za-z0-9_]*"
            r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
        )
    )


class PackagingSection(ManifestSection):
    executable_name: str = Field(
        pattern=r"^[A-Za-z0-9_-]+$"
    )
    installer_name: str = Field(
        pattern=r"^[A-Za-z0-9_-]+$"
    )


class ApplicationManifest(ManifestSection):
    schema_version: Literal[2]
    application: ApplicationSection
    runtime: RuntimeSection
    data: DataSection
    database: DatabaseSection
    email: EmailSection
    features: FeaturesSection
    development: DevelopmentSection
    packaging: PackagingSection


def load_application_manifest(
    path: Path | None = None,
) -> ApplicationManifest:
    manifest_path = (
        path
        if path is not None
        else get_application_manifest_path()
    )

    try:
        manifest_text = manifest_path.read_text(
            encoding="utf-8"
        )
    except OSError as error:
        raise RuntimeError(
            "Application manifest could not be read: "
            f"{manifest_path}"
        ) from error

    try:
        manifest_data = yaml.safe_load(
            manifest_text
        )
    except yaml.YAMLError as error:
        raise RuntimeError(
            "Application manifest contains invalid YAML."
        ) from error

    if not isinstance(manifest_data, dict):
        raise RuntimeError(
            "Application manifest must contain "
            "a YAML mapping."
        )

    try:
        return ApplicationManifest.model_validate(
            manifest_data
        )
    except ValidationError as error:
        raise RuntimeError(
            "Application manifest validation failed:\n"
            f"{error}"
        ) from error


@lru_cache(maxsize=1)
def get_application_manifest() -> ApplicationManifest:
    return load_application_manifest()