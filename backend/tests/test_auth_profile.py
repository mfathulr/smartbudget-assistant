"""Auth and profile flow tests using the seeded test user."""

from datetime import datetime, timezone


def login(client, email, password):
    resp = client.post(
        "/api/login",
        json={"email": email, "password": password, "remember": False},
    )
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()
    token = data.get("token")
    assert token
    return token


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_success_and_me(client, test_user):
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email"] == test_user["email"]
    assert data["role"] == "user"


def test_login_missing_fields_returns_400(client):
    resp = client.post("/api/login", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_profile_update_roundtrip(client, test_user):
    token = login(client, test_user["email"], test_user["password"])
    new_bio = f"Bio updated at {datetime.now(timezone.utc).isoformat()}"

    resp = client.put(
        "/api/me",
        headers=auth_headers(token),
        json={
            "name": "Test User",  # name is required by endpoint
            "bio": new_bio,
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini",
        },
    )
    assert resp.status_code == 200

    resp = client.get("/api/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("bio") == new_bio
    assert data.get("ai_provider") == "openai"
    assert data.get("ai_model") == "gpt-4o-mini"


def test_logout_calls_endpoint_successfully(client, test_user):
    """Test that logout endpoint responds 200; session cleanup is rolled back in tests."""
    token = login(client, test_user["email"], test_user["password"])
    resp = client.post("/api/logout", headers=auth_headers(token))
    assert resp.status_code == 200
    # Note: In test env with rollback fixture, session isn't truly deleted
    # This test just verifies the endpoint doesn't error
