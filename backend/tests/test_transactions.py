"""Transactions CRUD happy paths."""

from tests.test_auth_profile import login, auth_headers


def _create_tx(client, token, payload=None):
    body = {
        "type": "expense",
        "category": "Food",
        "description": "Lunch",
        "amount": 50000,
        "account": "Cash",
    }
    if payload:
        body.update(payload)
    return client.post("/api/transactions", json=body, headers=auth_headers(token))


def test_transaction_crud_flow(client, test_user):
    token = login(client, test_user["email"], test_user["password"])

    # Create
    resp = _create_tx(client, token)
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "ok"

    # List
    resp = client.get("/api/transactions", headers=auth_headers(token))
    assert resp.status_code == 200
    txs = resp.get_json()
    assert isinstance(txs, list)
    assert txs, "Expected at least one transaction after creation"
    tx_id = txs[0]["id"]

    # Update
    resp = client.put(
        f"/api/transactions/{tx_id}",
        headers=auth_headers(token),
        json={
            "amount": 75000,
            "type": "expense",
            "category": "Food",
            "description": "Lunch updated",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "ok"

    # Delete
    resp = client.delete(f"/api/transactions/{tx_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "ok"
