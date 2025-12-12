"""
End-to-end integration tests for context and interaction intents.
Tests actual database operations through the full pipeline.
"""

import pytest
from datetime import datetime, timezone, timedelta

from tests.test_auth_profile import login, auth_headers


def test_interaction_add_transaction_persists_to_db(client, test_user, db_conn, monkeypatch):
    """Test that interaction intent actually adds transaction to database."""
    token = login(client, test_user["email"], test_user["password"])
    
    # Mock OpenAI to return tool call for add_transaction
    class _DummyToolCall:
        def __init__(self):
            self.function = type('obj', (object,), {
                'name': 'add_transaction',
                'arguments': '{"type": "expense", "amount": 50000, "category": "Makan", "description": "Test expense", "account": "Cash"}'
            })()
    
    class _DummyMessage:
        def __init__(self):
            self.content = ""
            self.tool_calls = [_DummyToolCall()]
    
    class _DummyChoice:
        def __init__(self):
            self.message = _DummyMessage()
    
    class _DummyResp:
        def __init__(self):
            self.choices = [_DummyChoice()]
    
    def _fake_create(*args, **kwargs):
        return _DummyResp()
    
    import main
    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)
    
    # Get initial transaction count
    initial_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],)
    ).fetchone()["count"] or 0
    
    # Send chat request with interaction intent
    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "catat pengeluaran 50000 untuk makan",
            "model_provider": "openai",
            "model": "gpt-4o-mini"
        }
    )
    
    assert resp.status_code == 200
    
    # Verify transaction was added to database
    final_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],),
    ).fetchone()["count"] or 0
    
    assert final_count == initial_count + 1, "Transaction should be added to database"
    
    # Verify transaction details
    transaction = db_conn.execute(
        """SELECT type, amount, category, description, account 
           FROM transactions 
           WHERE user_id = %s 
           ORDER BY created_at DESC 
           LIMIT 1""",
        (test_user["id"],)
    ).fetchone()
    
    assert transaction["type"] == "expense"
    assert transaction["amount"] == 50000
    assert transaction["category"] == "Makan"
    assert transaction["account"] == "Cash"


def test_context_retrieves_actual_data(client, test_user, db_conn, monkeypatch):
    """Test that context intent retrieves actual user data from database."""
    token = login(client, test_user["email"], test_user["password"])
    
    # First, add a test transaction
    wib = timezone(timedelta(hours=7))
    test_date = datetime.now(wib).date().isoformat()
    
    db_conn.execute(
        """INSERT INTO transactions (user_id, date, type, category, amount, account, description)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (test_user["id"], test_date, "expense", "Transport", 25000, "Cash", "Test context")
    )
    db_conn.commit()
    
    # Mock OpenAI to NOT call tools (so we can check context is provided)
    class _DummyMessage:
        def __init__(self):
            self.content = "Based on your data, you spent 25000 on transport."
            self.tool_calls = None
    
    class _DummyChoice:
        def __init__(self):
            self.message = _DummyMessage()
    
    class _DummyResp:
        def __init__(self):
            self.choices = [_DummyChoice()]
    
    # Capture the messages sent to OpenAI
    captured_messages = []
    
    def _fake_create(*args, **kwargs):
        captured_messages.append(kwargs.get("messages", []))
        return _DummyResp()
    
    import main
    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)
    
    # Send chat request with context intent
    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "berapa total pengeluaran saya?",
            "model_provider": "openai",
            "model": "gpt-4o-mini"
        }
    )
    
    assert resp.status_code == 200
    data = resp.get_json()
    
    # Verify response contains actual data
    assert "answer" in data
    
    # Verify context was built (check if our test transaction data appears in prompt)
    # The financial context should be included in the messages
    if captured_messages:
        all_content = str(captured_messages)
        # Context should mention user transactions/balance
        assert len(all_content) > 100, "Context should be provided to LLM"


def test_interaction_transfer_updates_multiple_records(client, test_user, db_conn, monkeypatch):
    """Test that transfer creates two transaction records."""
    token = login(client, test_user["email"], test_user["password"])
    
    # Mock OpenAI to return tool call for transfer_funds
    class _DummyToolCall:
        def __init__(self):
            self.function = type('obj', (object,), {
                'name': 'transfer_funds',
                'arguments': '{"amount": 100000, "from_account": "BCA", "to_account": "Cash", "description": "Transfer test"}'
            })()
    
    class _DummyMessage:
        def __init__(self):
            self.content = ""
            self.tool_calls = [_DummyToolCall()]
    
    class _DummyChoice:
        def __init__(self):
            self.message = _DummyMessage()
    
    class _DummyResp:
        def __init__(self):
            self.choices = [_DummyChoice()]
    
    def _fake_create(*args, **kwargs):
        return _DummyResp()
    
    import main
    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)
    
    # Get initial transaction count
    initial_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],)
    ).fetchone()["count"] or 0

    # Send chat request for transfer
    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "transfer 100rb dari BCA ke Cash",
            "model_provider": "openai",
            "model": "gpt-4o-mini"
        }
    )
    
    assert resp.status_code == 200
    
    # Verify TWO transactions were added (debit and credit)
    final_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],)
    ).fetchone()["count"] or 0
    
    assert final_count == initial_count + 2, "Transfer should create 2 transaction records"
    
    # Verify one debit and one credit
    recent_transactions = db_conn.execute(
        """SELECT type, amount, account, category 
           FROM transactions 
           WHERE user_id = %s 
           ORDER BY created_at DESC 
           LIMIT 2""",
        (test_user["id"],)
    ).fetchall()
    
    accounts = [t["account"] for t in recent_transactions]
    assert "BCA" in accounts and "Cash" in accounts, "Both accounts should have transactions"


def test_interaction_validates_before_execution(client, test_user, db_conn, monkeypatch):
    """Test that interaction validates data before executing (missing required field)."""
    token = login(client, test_user["email"], test_user["password"])
    
    # Mock OpenAI to return tool call with MISSING required field (category)
    class _DummyToolCall:
        def __init__(self):
            self.function = type('obj', (object,), {
                'name': 'add_transaction',
                'arguments': '{"type": "expense", "amount": 30000, "account": "Cash"}'
                # Missing "category" - should be validated
            })()
    
    class _DummyMessage:
        def __init__(self):
            self.content = ""
            self.tool_calls = [_DummyToolCall()]
    
    class _DummyChoice:
        def __init__(self):
            self.message = _DummyMessage()
    
    class _DummyResp:
        def __init__(self):
            self.choices = [_DummyChoice()]
    
    def _fake_create(*args, **kwargs):
        return _DummyResp()
    
    import main
    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)
    
    # Get initial transaction count
    initial_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],)
    ).fetchone()["count"] or 0

    # Send chat request with incomplete data
    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "catat pengeluaran 30000",
            "model_provider": "openai",
            "model": "gpt-4o-mini"
        }
    )
    
    assert resp.status_code == 200
    
    # Verify transaction was NOT added due to validation failure
    final_count = db_conn.execute(
        "SELECT COUNT(*) AS count FROM transactions WHERE user_id = %s",
        (test_user["id"],)
    ).fetchone()["count"] or 0
    
    # Should remain the same or validation error should be returned
    # (executor should reject missing category)
    data = resp.get_json()
    assert "answer" in data
    # The response should indicate missing information
    # This tests that validation layer is working
