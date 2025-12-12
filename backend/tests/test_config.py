"""Tests for config module."""

import os


def test_config_has_required_env_vars():
    """Test required environment variables are set."""
    required_vars = ["DATABASE_URL", "SECRET_KEY"]

    for var in required_vars:
        assert os.getenv(var), f"Environment variable {var} must be set"


def test_database_url_uses_postgresql():
    """Test DATABASE_URL is PostgreSQL (not SQLite)."""
    db_url = os.getenv("DATABASE_URL", "")
    assert "postgresql://" in db_url or "postgres://" in db_url, (
        "DATABASE_URL must use PostgreSQL"
    )


def test_config_imports_without_error():
    """Test config module can be imported."""
    try:
        from config import (
            BASE_DIR,
            FLASK_CONFIG,
            DATABASE_URL,
            DB_TYPE,
        )

        assert BASE_DIR is not None
        assert FLASK_CONFIG is not None
        assert DATABASE_URL is not None
        assert DB_TYPE == "postgresql"
    except ImportError as e:
        raise AssertionError(f"Config import failed: {e}")
