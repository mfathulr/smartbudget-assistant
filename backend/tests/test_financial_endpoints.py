"""Tests for balance and summary endpoints."""

from tests.test_auth_profile import login, auth_headers


def test_balance_endpoint(client, test_user):
    """Test balance calculation endpoint."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/balance", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "balance" in data
    assert isinstance(data["balance"], (int, float))


def test_balance_with_account_filter(client, test_user):
    """Test balance filtered by account."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/balance?account=Cash", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "balance" in data


def test_summary_endpoint(client, test_user):
    """Test monthly summary endpoint."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/summary", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    # API returns: total_income, total_expense, net
    assert "total_income" in data
    assert "total_expense" in data
    assert "net" in data


def test_summary_with_year_month(client, test_user):
    """Test summary with specific year and month."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/summary?year=2024&month=12", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total_income" in data


def test_accounts_endpoint(client, test_user):
    """Test accounts list endpoint."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.get("/api/accounts", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    # API returns dict with 'accounts' key containing list
    assert isinstance(data, dict)
    assert "accounts" in data
    assert isinstance(data["accounts"], list)
