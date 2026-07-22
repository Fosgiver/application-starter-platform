from app.core.manifest import (
    load_application_manifest,
)


def test_application_manifest_loads() -> None:
    manifest = load_application_manifest()

    assert manifest.schema_version == 2
    assert manifest.application.name.strip()
    assert manifest.application.version.strip()

    assert manifest.runtime.host == "127.0.0.1"
    assert manifest.runtime.port == 8000

    assert (
        manifest.development.domain_package
        == "app.domain"
    )

    technical_name = "".join(
        part.capitalize()
        for part
        in manifest.application.slug.split("-")
    )

    assert (
        manifest.data.directory_name
        == technical_name
    )
    assert (
        manifest.packaging.executable_name
        == technical_name
    )
    assert (
        manifest.packaging.installer_name
        == f"{technical_name}_Setup"
    )

    assert not hasattr(
        manifest.database,
        "engine",
    )
    assert not hasattr(
        manifest.database,
        "sqlite_filename",
    )

    assert manifest.email.from_name.strip()
