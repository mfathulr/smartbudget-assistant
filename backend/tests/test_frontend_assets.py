"""Sanity checks for critical frontend assets to ensure files exist and are not empty."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _assert_non_empty(file_path: Path):
    assert file_path.exists(), f"Missing file: {file_path}"
    assert file_path.is_file(), f"Not a file: {file_path}"
    assert file_path.stat().st_size > 0, f"Empty file: {file_path}"


def test_public_index_and_settings_exist():
    for rel in [
        "public/index.html",
        "public/admin.html",
        "public/login.html",
        "public/settings.html",
    ]:
        _assert_non_empty(BASE_DIR / rel)


def test_static_assets_exist():
    for rel in [
        "public/static/app.js",
        "public/static/styles.css",
        "public/static/modals.js",
    ]:
        _assert_non_empty(BASE_DIR / rel)
