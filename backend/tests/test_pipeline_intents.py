"""Tests for ChatPipelineManager intent routing and handlers (classification driven)."""

from pipeline.manager import ChatPipelineManager
from services.intent_classifier import IntentClassifier


def _mock_classify(
    monkeypatch, category: str, intent_type: str, confidence: float = 0.9
):
    """Patch IntentClassifier.classify to return a fixed tuple."""
    monkeypatch.setattr(
        IntentClassifier,
        "classify",
        classmethod(lambda cls, query: (category, intent_type, confidence)),
    )


def test_pipeline_general_uses_llm_without_context(monkeypatch):
    """General intent should always use LLM without data context."""
    _mock_classify(monkeypatch, "general", "education")
    pipeline = ChatPipelineManager(db=None, user_id=1, language="id")

    result = pipeline.process_query("apa itu budget?")

    assert result["success"] is False
    assert result["fallback_to_llm"] is True
    assert result["requires_context"] is False
    assert result["requires_data_query"] is False
    assert result["response_type"] == "general"
    assert "Focus on fundamentals" in result["prompt_hint"]
    assert "No tools" in result["prompt_hint"]
    assert result["intent_category"] == "general"
    assert result["intent_type"] == "education"


def test_pipeline_general_help_uses_llm(monkeypatch):
    """General help intent should use LLM without data query."""
    _mock_classify(monkeypatch, "general", "help")
    pipeline = ChatPipelineManager(db=None, user_id=1, language="id")

    result = pipeline.process_query("bantu saya dengan fitur")

    assert result["success"] is False
    assert result.get("fallback_to_llm") is True
    assert result.get("requires_data_query") is False
    assert "Answer briefly" in result["prompt_hint"]
    assert "No tools" in result["prompt_hint"]
    assert result["intent_category"] == "general"


def test_pipeline_context_requires_data_query(monkeypatch):
    """Context data intent should require data query and use LLM."""
    _mock_classify(monkeypatch, "context_data", "summary")
    pipeline = ChatPipelineManager(db=None, user_id=1, language="id")

    result = pipeline.process_query("tolong summary pengeluaran saya")

    assert result["success"] is False
    assert result.get("fallback_to_llm") is True
    assert result.get("requires_context") is True
    assert result.get("requires_data_query") is True
    assert result.get("response_type") == "context_data"
    assert "Use tools" in result.get("prompt_hint", "")
    assert "Ask if missing" in result.get("prompt_hint", "")
    assert result["intent_category"] == "context_data"


def test_pipeline_interaction_requires_validation(monkeypatch):
    """Interaction data intent should require context, data query, and validation."""
    _mock_classify(monkeypatch, "interaction_data", "record")
    pipeline = ChatPipelineManager(db=None, user_id=1, language="id")

    result = pipeline.process_query("catat pengeluaran 10000 untuk makan")

    assert result["success"] is False
    assert result.get("fallback_to_llm") is True
    assert result.get("requires_context") is True
    assert result.get("requires_data_query") is True
    assert result.get("requires_validation") is True
    assert result.get("response_type") == "interaction_data"
    assert "Collect:" in result.get("prompt_hint", "")
    assert "Confirm" in result.get("prompt_hint", "")
    assert "Validate" in result.get("prompt_hint", "")
    assert result["intent_category"] == "interaction_data"


def test_pipeline_unknown_intent_category(monkeypatch):
    """Unknown intent category returns error without raising."""
    _mock_classify(monkeypatch, "unknown", "whatever")
    pipeline = ChatPipelineManager(db=None, user_id=1, language="id")

    result = pipeline.process_query("some query")

    assert result["success"] is False
    assert "Unknown intent category" in result["error"]
    assert result.get("fallback_to_llm") is None
