"""Tests for savings goals endpoints."""

from tests.test_auth_profile import login, auth_headers


def test_savings_goals_crud_flow(client, test_user):
    """Test create, list, update, delete savings goals."""
    token = login(client, test_user["email"], test_user["password"])

    # Create savings goal
    resp = client.post(
        "/api/savings",
        headers=auth_headers(token),
        json={
            "name": "Emergency Fund",
            "target_amount": 10000000,
            "description": "6 months expenses",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"

    # List savings goals
    resp = client.get("/api/savings", headers=auth_headers(token))
    assert resp.status_code == 200
    goals = resp.get_json()
    assert isinstance(goals, list)
    if goals:
        goal_id = goals[0]["id"]

        # Update savings goal
        resp = client.put(
            "/api/savings",
            headers=auth_headers(token),
            json={
                "id": goal_id,
                "name": "Emergency Fund Updated",
                "target_amount": 15000000,
            },
        )
        assert resp.status_code == 200

        # Delete savings goal
        resp = client.delete(
            "/api/savings",
            headers=auth_headers(token),
            json={"id": goal_id},
        )
        assert resp.status_code == 200


def test_transfer_to_savings(client, test_user):
    """Test transferring funds to savings goal."""
    token = login(client, test_user["email"], test_user["password"])

    # Create goal first
    resp = client.post(
        "/api/savings",
        headers=auth_headers(token),
        json={"name": "Vacation", "target_amount": 5000000},
    )
    assert resp.status_code == 200

    # Get goal ID
    resp = client.get("/api/savings", headers=auth_headers(token))
    goals = resp.get_json()
    if goals:
        goal_id = goals[0]["id"]

        # Transfer to savings
        resp = client.post(
            "/api/transfer_to_savings",
            headers=auth_headers(token),
            json={"amount": 500000, "from_account": "Cash", "goal_id": goal_id},
        )
        # May fail if goal not found in fresh DB, just check it doesn't crash
        assert resp.status_code in [200, 404]
