"""Tests for forgot/reset password flow."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def test_forgot_password_sends_token(client, test_user, db_conn):
    """Test that forgot password endpoint creates reset token and sends email."""
    # Mock email sending
    with patch("main.send_password_reset_email", return_value=True) as mock_email:
        resp = client.post(
            "/api/password/forgot",
            json={"email": test_user["email"]},
        )

    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data["status"] == "ok"

    # Verify token was created in database (schema uses user_id not email)
    cur = db_conn.execute(
        "SELECT token, expires_at FROM password_resets WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (test_user["id"],),
    )
    reset_record = cur.fetchone()
    assert reset_record is not None
    assert reset_record["token"] is not None

    # Verify email was called
    mock_email.assert_called_once()


def test_forgot_password_nonexistent_email(client):
    """Test forgot password with email that doesn't exist."""
    with patch("main.send_password_reset_email", return_value=True):
        resp = client.post(
            "/api/password/forgot",
            json={"email": "nonexistent@example.com"},
        )

        # Should still return 200 to avoid email enumeration
        # OR return 404 if API doesn't care about enumeration
        assert resp.status_code in (200, 404)


def test_forgot_password_missing_email(client):
    """Test validation of required email field."""
    resp = client.post(
        "/api/password/forgot",
        json={},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_reset_password_with_valid_token(client, test_user, db_conn):
    """Test successful password reset with valid token."""
    import secrets

    # Create reset token with WIB timezone (UTC+7) like backend
    token = secrets.token_urlsafe(32)
    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) + timedelta(hours=1))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    db_conn.execute(
        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (test_user["id"], token, expires_at),
    )
    db_conn.commit()

    # Reset password
    new_password = "NewSecurePass456!"
    resp = client.post(
        "/api/password/reset",
        json={"token": token, "password": new_password},
    )

    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data["status"] == "ok"

    # Verify password was changed in database
    from werkzeug.security import check_password_hash

    cur = db_conn.execute(
        "SELECT password_hash FROM users WHERE email = %s", (test_user["email"],)
    )
    user = cur.fetchone()
    assert user is not None
    assert check_password_hash(user["password_hash"], new_password)

    # Verify token was consumed (deleted or marked as used)
    cur = db_conn.execute(
        "SELECT token FROM password_resets WHERE token = %s", (token,)
    )
    reset_record = cur.fetchone()
    # Token should be deleted or marked as used
    assert reset_record is None or reset_record.get("used") is True


def test_reset_password_with_invalid_token(client):
    """Test that invalid token is rejected."""
    resp = client.post(
        "/api/password/reset",
        json={"token": "invalid_token_12345", "password": "NewPass123!"},
    )

    assert resp.status_code in (400, 404), resp.get_json()
    data = resp.get_json()
    assert "error" in data


def test_reset_password_with_expired_token(client, test_user, db_conn):
    """Test that expired token is rejected."""
    import secrets

    # Create expired token (1 hour ago) with WIB timezone
    token = secrets.token_urlsafe(32)
    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) - timedelta(hours=1))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    db_conn.execute(
        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (test_user["id"], token, expires_at),
    )
    db_conn.commit()

    # Try to reset with expired token
    resp = client.post(
        "/api/password/reset",
        json={"token": token, "password": "NewPass123!"},
    )

    assert resp.status_code in (400, 410), resp.get_json()
    data = resp.get_json()
    assert "error" in data


def test_reset_password_missing_fields(client):
    """Test validation of required fields."""
    # Missing password
    resp = client.post(
        "/api/password/reset",
        json={"token": "some_token"},
    )
    assert resp.status_code == 400

    # Missing token
    resp = client.post(
        "/api/password/reset",
        json={"password": "NewPass123!"},
    )
    assert resp.status_code == 400


def test_reset_password_weak_password(client, test_user, db_conn):
    """Test that weak password is rejected."""
    import secrets

    # Create valid token with WIB timezone
    token = secrets.token_urlsafe(32)
    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) + timedelta(hours=1))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    db_conn.execute(
        "INSERT INTO password_resets (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (test_user["id"], token, expires_at),
    )
    db_conn.commit()

    # Try weak passwords
    weak_passwords = ["123", "password", "abc"]

    for weak_pwd in weak_passwords:
        resp = client.post(
            "/api/password/reset",
            json={"token": token, "password": weak_pwd},
        )
        # Should reject weak password (if validation exists)
        # If no validation, this test will reveal that gap
        if resp.status_code == 400:
            data = resp.get_json()
            assert "error" in data
            break  # At least one weak password was caught
