"""Tests for user registration flow with OTP verification."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


def test_register_send_otp_success(client, db_conn):
    """Test sending OTP for new user registration."""
    email = "newuser@example.com"
    name = "New User"
    password = "SecurePass123!"

    # Clean up if exists
    db_conn.execute("DELETE FROM registration_otps WHERE email = %s", (email,))
    db_conn.execute("DELETE FROM users WHERE email = %s", (email,))
    db_conn.commit()

    # Mock email sending to avoid actual SMTP
    with patch("main.send_otp_email", return_value=True):
        resp = client.post(
            "/api/register/send-otp",
            json={"name": name, "email": email, "password": password},
        )

    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "otp_sent" in data or "message" in data

    # Verify OTP was stored in database
    cur = db_conn.execute(
        "SELECT email, expires_at FROM registration_otps WHERE email = %s", (email,)
    )
    otp_record = cur.fetchone()
    assert otp_record is not None
    assert otp_record["email"] == email


def test_register_send_otp_existing_email(client, test_user):
    """Test that registration fails for existing email."""
    with patch("main.send_otp_email", return_value=True):
        resp = client.post(
            "/api/register/send-otp",
            json={
                "name": "Test User",
                "email": test_user["email"],  # Already exists
                "password": "AnotherPass123!",
            },
        )

    # Should reject with 400 or 409
    assert resp.status_code in (400, 409), resp.get_json()
    data = resp.get_json()
    assert "error" in data


def test_register_send_otp_missing_fields(client):
    """Test validation of required fields."""
    resp = client.post(
        "/api/register/send-otp",
        json={"email": "test@example.com"},  # Missing name and password
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_register_verify_otp_success(client, db_conn):
    """Test successful OTP verification and user creation."""
    email = "verifytest@example.com"
    name = "Verify Test"
    password = "TestPass123!"
    otp_code = "123456"

    # Clean up
    db_conn.execute("DELETE FROM registration_otps WHERE email = %s", (email,))
    db_conn.execute("DELETE FROM users WHERE email = %s", (email,))
    db_conn.commit()

    # Insert OTP directly (simulate send-otp step)
    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) + timedelta(minutes=10))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    from werkzeug.security import generate_password_hash

    pwd_hash = generate_password_hash(password)

    db_conn.execute(
        "INSERT INTO registration_otps (email, name, password_hash, otp_code, expires_at) VALUES (%s, %s, %s, %s, %s)",
        (email, name, pwd_hash, otp_code, expires_at),
    )
    db_conn.commit()

    # Verify OTP
    resp = client.post(
        "/api/register/verify-otp",
        json={"email": email, "otp": otp_code},
    )

    assert resp.status_code in (200, 201), (
        resp.get_json()
    )  # Accept both 200 OK and 201 Created
    data = resp.get_json()
    assert data["status"] == "ok"

    # Verify user was created
    cur = db_conn.execute(
        "SELECT id, email, name FROM users WHERE email = %s", (email,)
    )
    user = cur.fetchone()
    assert user is not None
    assert user["email"] == email
    assert user["name"] == name

    # Verify OTP was deleted
    cur = db_conn.execute(
        "SELECT email FROM registration_otps WHERE email = %s", (email,)
    )
    otp_record = cur.fetchone()
    assert otp_record is None


def test_register_verify_otp_wrong_code(client, db_conn):
    """Test that wrong OTP code is rejected."""
    email = "wrongotp@example.com"
    correct_otp = "123456"
    wrong_otp = "999999"

    # Clean up and insert OTP
    db_conn.execute("DELETE FROM registration_otps WHERE email = %s", (email,))
    db_conn.execute("DELETE FROM users WHERE email = %s", (email,))
    db_conn.commit()

    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) + timedelta(minutes=10))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    from werkzeug.security import generate_password_hash

    db_conn.execute(
        "INSERT INTO registration_otps (email, name, password_hash, otp_code, expires_at) VALUES (%s, %s, %s, %s, %s)",
        (email, "Test", generate_password_hash("Pass123!"), correct_otp, expires_at),
    )
    db_conn.commit()

    # Try with wrong OTP
    resp = client.post(
        "/api/register/verify-otp",
        json={"email": email, "otp": wrong_otp},
    )

    assert resp.status_code in (400, 401), resp.get_json()
    data = resp.get_json()
    assert "error" in data

    # Verify user was NOT created
    cur = db_conn.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    assert user is None


def test_register_verify_otp_expired(client, db_conn):
    """Test that expired OTP is rejected."""
    email = "expiredotp@example.com"
    otp_code = "123456"

    # Clean up
    db_conn.execute("DELETE FROM registration_otps WHERE email = %s", (email,))
    db_conn.execute("DELETE FROM users WHERE email = %s", (email,))
    db_conn.commit()

    # Insert expired OTP (1 hour ago) with WIB timezone
    wib = timezone(timedelta(hours=7))
    expires_at = (
        (datetime.now(wib) - timedelta(hours=1))
        .replace(tzinfo=None)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    from werkzeug.security import generate_password_hash

    db_conn.execute(
        "INSERT INTO registration_otps (email, name, password_hash, otp_code, expires_at) VALUES (%s, %s, %s, %s, %s)",
        (email, "Test", generate_password_hash("Pass123!"), otp_code, expires_at),
    )
    db_conn.commit()

    # Try to verify expired OTP
    resp = client.post(
        "/api/register/verify-otp",
        json={"email": email, "otp": otp_code},
    )

    assert resp.status_code in (400, 410), resp.get_json()
    data = resp.get_json()
    assert "error" in data
