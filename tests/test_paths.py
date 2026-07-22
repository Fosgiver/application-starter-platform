from pathlib import Path

import pytest

from app.core import paths


def test_bundled_data_directory_uses_application_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "APP_DATA_DIRECTORY",
        raising=False,
    )
    monkeypatch.setenv(
        "LOCALAPPDATA",
        str(tmp_path),
    )
    monkeypatch.setattr(
        paths,
        "is_bundled_application",
        lambda: True,
    )

    assert paths.get_data_directory() == (
        tmp_path
        / paths.APPLICATION_DATA_DIRECTORY_NAME
        / "Data"
    )


def test_database_path_uses_application_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        paths,
        "get_data_directory",
        lambda: tmp_path,
    )

    assert paths.get_database_file_path() == (
        tmp_path
        / paths.APPLICATION_DATABASE_FILENAME
    )
