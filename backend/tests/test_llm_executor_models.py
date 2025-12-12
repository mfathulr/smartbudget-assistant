"""LLM executor and tools tests (model-agnostic, using gpt-4o-mini scenario)."""

from llm.executor import execute_action, _parse_amount
import llm.executor as executor_mod
import llm.tools as tools_mod


def test_execute_add_transaction_routes_to_handler(monkeypatch):
    """Ensure execute_action routes add_transaction to its handler."""
    called = {}

    def fake_handler(user_id, action_name, args):
        called["user_id"] = user_id
        called["action"] = action_name
        called["args"] = args
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(executor_mod, "_execute_add_transaction", fake_handler)

    result = execute_action(
        user_id=42,
        action_name="add_transaction",
        args={"type": "expense", "amount": "15.000", "category": "Food"},
    )

    assert result["success"] is True
    assert called["user_id"] == 42
    assert called["action"] == "add_transaction"
    assert called["args"]["category"] == "Food"


def test_execute_add_transaction_error_handling(monkeypatch):
    """If handler raises, execute_action returns EXECUTION_ERROR."""

    def fake_handler(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(executor_mod, "_execute_add_transaction", fake_handler)

    result = execute_action(
        user_id=7,
        action_name="add_transaction",
        args={"type": "expense", "amount": 1000},
    )

    assert result["success"] is False
    assert result["code"] == "EXECUTION_ERROR"


def test_execute_unknown_action_returns_error():
    result = execute_action(user_id=1, action_name="unknown_action", args={})
    assert result["success"] is False
    assert result["code"] == "UNKNOWN_ACTION"


def test_parse_amount_supports_indonesian_formats():
    assert _parse_amount("5 juta") == 5_000_000
    assert _parse_amount("25.000") == 25000
    assert _parse_amount("1,5 juta") == 1_500_000
    assert _parse_amount("10k") == 10_000


def test_tools_definitions_contain_core_actions():
    tool_names = {t["function"]["name"] for t in tools_mod.TOOLS_DEFINITIONS}
    expected = {
        "add_transaction",
        "create_savings_goal",
        "update_transaction",
        "delete_transaction",
        "transfer_funds",
    }
    assert expected.issubset(tool_names)
    # Ensure schema contains required keys
    for tool in tools_mod.TOOLS_DEFINITIONS:
        assert tool.get("type") == "function"
        fn = tool.get("function", {})
        assert "name" in fn and "parameters" in fn
