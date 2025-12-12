"""Tests for admin role and permissions."""

from tests.test_auth_profile import login, auth_headers


def test_admin_cannot_access_with_user_role(client, test_user):
    """Regular user should not access admin endpoints."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/admin/users", headers=auth_headers(token))
    assert resp.status_code == 403  # Forbidden


def test_unauthorized_access_to_admin(client):
    """Unauthenticated request should return 401."""
    resp = client.get("/api/admin/users")
    assert resp.status_code == 401


def test_protected_endpoints_require_auth(client):
    """Test that protected endpoints reject unauthenticated requests."""
    endpoints = [
        ("/api/me", "GET"),
        ("/api/transactions", "GET"),
        ("/api/summary", "GET"),
        ("/api/balance", "GET"),
        ("/api/savings", "GET"),
        ("/api/chat", "POST"),
    ]

    for path, method in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json={})
        assert resp.status_code == 401, f"{method} {path} should return 401"
