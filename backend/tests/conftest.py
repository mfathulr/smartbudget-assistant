"""Pytest configuration for backend tests.
Sets safe default environment variables so config import does not fail.
"""

import os
import pytest
from _pytest.monkeypatch import MonkeyPatch
from werkzeug.security import generate_password_hash

from main import app
from database import get_db, init_db


@pytest.fixture(scope="session", autouse=True)
def _test_env():
    """Ensure required env vars exist during tests without touching real secrets."""
    mp = MonkeyPatch()
    mp.setenv(
        "DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://test_user:test_pass@localhost:5432/test_db",
        ),
    )
    mp.setenv("SECRET_KEY", os.getenv("SECRET_KEY", "test-secret-key"))
    mp.setenv("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "test-openai-key"))
    mp.setenv("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", "test-google-key"))
    mp.setenv("RECAPTCHA_SITE_KEY", os.getenv("RECAPTCHA_SITE_KEY", ""))
    mp.setenv("RECAPTCHA_SECRET_KEY", os.getenv("RECAPTCHA_SECRET_KEY", ""))
    yield
    mp.undo()


@pytest.fixture(scope="session")
def app_ctx(_test_env):
    """Provide app context and initialize schema once for tests."""
    with app.app_context():
        try:
            init_db()
        except Exception as exc:  # pragma: no cover - handled by skip
            pytest.skip(f"Database not available for tests: {exc}")
        yield


@pytest.fixture()
def db_conn(app_ctx):
    """Database connection via adapter; commits normally during tests."""
    db = get_db()
    yield db
    # After each test, check if there's a failed transaction and rollback
    try:
        # Try a simple query to see if transaction is alive
        db.execute("SELECT 1")
    except Exception:
        # Transaction is dead, rollback and start fresh
        try:
            db.rollback()
        except Exception:
            pass


@pytest.fixture()
def client(app_ctx):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def test_user(app_ctx, db_conn):
    """Create or fetch a standard test user and return its credentials."""
    email = "testuser@example.com"
    password = "Password123!"

    # Check if user already exists
    cur = db_conn.execute(
        "SELECT id, password_hash FROM users WHERE email = %s", (email,)
    )
    existing = cur.fetchone()

    if existing:
        # Verify the password hash matches
        from werkzeug.security import check_password_hash

        if check_password_hash(existing["password_hash"], password):
            print(f"[TEST SETUP] Reusing existing user ID: {existing['id']}")
            return {"id": existing["id"], "email": email, "password": password}
        else:
            # Password mismatch - need to update it
            print(f"[TEST SETUP] Updating password for user ID: {existing['id']}")
            pwd_hash = generate_password_hash(password)
            db_conn.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (pwd_hash, existing["id"]),
            )
            db_conn.commit()
            return {"id": existing["id"], "email": email, "password": password}

    # Create fresh user if doesn't exist
    pwd_hash = generate_password_hash(password)
    print(f"[TEST SETUP] Creating new user with email: {email}")
    db_conn.execute(
        "INSERT INTO users (name, email, password_hash, role, ocr_enabled) VALUES (%s, %s, %s, %s, %s)",
        ("Test User", email, pwd_hash, "user", True),
    )
    db_conn.commit()

    cur = db_conn.execute("SELECT id FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    print(f"[TEST SETUP] User created with ID: {row['id']}")

    return {"id": row["id"], "email": email, "password": password}
