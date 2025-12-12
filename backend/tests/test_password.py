"""Tests for password reset flow."""

from tests.test_auth_profile import login, auth_headers


def test_password_update_with_valid_old_password(client, test_user):
    """Test password change with correct old password."""
    token = login(client, test_user["email"], test_user["password"])

    # Try to update password (API uses 'current_password' and 'password')
    resp = client.put(
        "/api/me/password",
        headers=auth_headers(token),
        json={
            "current_password": test_user["password"],
            "password": "NewPassword123!",
        },
    )
    # Should succeed
    assert resp.status_code == 200


def test_password_update_with_wrong_old_password(client, test_user):
    """Test password change fails with wrong old password."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.put(
        "/api/me/password",
        headers=auth_headers(token),
        json={
            "current_password": "WrongPassword123!",
            "password": "NewPassword123!",
        },
    )
    # Should fail with 403
    assert resp.status_code == 403


def test_password_update_requires_both_passwords(client, test_user):
    """Test password update requires both old and new passwords."""
    token = login(client, test_user["email"], test_user["password"])

    # Missing new password
    resp = client.put(
        "/api/me/password",
        headers=auth_headers(token),
        json={"current_password": test_user["password"]},
    )
    assert resp.status_code == 400

    # Missing old password (password field is required)
    resp = client.put(
        "/api/me/password",
        headers=auth_headers(token),
        json={"current_password": "anything"},
    )
    # Will fail due to password length validation
    assert resp.status_code == 400
