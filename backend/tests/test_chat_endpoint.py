"""
Chat endpoint tests with multiple AI models.
Tests that chatbot uses user-selected model and responds correctly for each provider.
"""

import pytest
import google.generativeai as genai

import main
from tests.test_auth_profile import login, auth_headers


# === OpenAI Mock Classes ===
class _DummyMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _DummyChoice:
    def __init__(self, content):
        self.message = _DummyMessage(content)


class _DummyResp:
    def __init__(self, content):
        self.choices = [_DummyChoice(content)]


# === Gemini Mock Classes ===
class _MockGeminiResponse:
    def __init__(self, text):
        self.text = text


class _MockGeminiModel:
    def __init__(self, model_name):
        self.model_name = model_name

    def generate_content(self, prompt, **kwargs):
        return _MockGeminiResponse(
            f"Gemini {self.model_name} response: Test successful"
        )


# === Test: OpenAI Model Selection ===
@pytest.mark.parametrize(
    "model_id",
    [
        "gpt-4o-mini",
    ],
)
def test_chat_openai_with_different_models(client, test_user, monkeypatch, model_id):
    """Test that OpenAI chat works with different GPT models."""
    token = login(client, test_user["email"], test_user["password"])

    # Track which model was actually used
    called_with_model = []

    def _fake_create(*args, **kwargs):
        called_with_model.append(kwargs.get("model"))
        return _DummyResp(f"Response from {kwargs.get('model')}")

    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)

    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Hello, test message",
            "model_provider": "openai",
            "model": model_id,
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "answer" in data
    assert model_id in data["answer"]
    assert called_with_model[0] == model_id, (
        f"Expected model {model_id}, got {called_with_model[0]}"
    )


# === Test: Gemini Model Selection ===
@pytest.mark.parametrize(
    "model_id",
    [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ],
)
def test_chat_gemini_with_different_models(client, test_user, monkeypatch, model_id):
    """Test that Gemini chat works with different Gemini models."""
    token = login(client, test_user["email"], test_user["password"])

    # Track which model was instantiated
    instantiated_models = []

    def _mock_generative_model(model_name, **kwargs):
        instantiated_models.append(model_name)
        return _MockGeminiModel(model_name)

    monkeypatch.setattr(genai, "GenerativeModel", _mock_generative_model)

    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Halo, ini test",
            "model_provider": "google",
            "model": model_id,
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "answer" in data
    assert model_id in data["answer"]
    assert instantiated_models[0] == model_id, (
        f"Expected model {model_id}, got {instantiated_models[0]}"
    )


# === Test: User Profile Model Preference ===
def test_chat_uses_user_profile_model_preference(
    client, test_user, db_conn, monkeypatch
):
    """Test that chat uses ai_model from user profile when no model specified."""
    token = login(client, test_user["email"], test_user["password"])

    # Update user profile to use specific model
    db_conn.execute(
        "UPDATE users SET ai_provider = %s, ai_model = %s WHERE email = %s",
        ("google", "gemini-2.5-flash", test_user["email"]),
    )
    db_conn.commit()

    # Track which model was instantiated
    instantiated_models = []

    def _mock_generative_model(model_name, **kwargs):
        instantiated_models.append(model_name)
        return _MockGeminiModel(model_name)

    monkeypatch.setattr(genai, "GenerativeModel", _mock_generative_model)

    # Send chat request without specifying model (should use profile default)
    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test using profile model",
            "model_provider": "google",
            # Note: no "model" parameter - should fallback to provider default
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "answer" in data
    # Should use provider default (gemini-2.5-flash) when model not specified
    assert instantiated_models[0] == "gemini-2.5-flash"


# === Test: Model Switching Between Providers ===
def test_chat_switches_between_openai_and_gemini(client, test_user, monkeypatch):
    """Test that chat can switch between OpenAI and Gemini providers."""
    token = login(client, test_user["email"], test_user["password"])

    # Mock OpenAI
    openai_called = []

    def _fake_openai_create(*args, **kwargs):
        openai_called.append(kwargs.get("model"))
        return _DummyResp(f"OpenAI response from {kwargs.get('model')}")

    monkeypatch.setattr(main.client.chat.completions, "create", _fake_openai_create)

    # Mock Gemini
    gemini_called = []

    def _mock_generative_model(model_name, **kwargs):
        gemini_called.append(model_name)
        return _MockGeminiModel(model_name)

    monkeypatch.setattr(genai, "GenerativeModel", _mock_generative_model)

    # Test 1: Use OpenAI
    resp1 = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test OpenAI",
            "model_provider": "openai",
            "model": "gpt-4o-mini",
        },
    )
    assert resp1.status_code == 200
    assert len(openai_called) == 1
    assert openai_called[0] == "gpt-4o-mini"

    # Test 2: Switch to Gemini
    resp2 = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test Gemini",
            "model_provider": "google",
            "model": "gemini-2.5-flash",
        },
    )
    assert resp2.status_code == 200
    assert len(gemini_called) == 1
    assert gemini_called[0] == "gemini-2.5-flash"


# === Test: Invalid Provider Handling ===
def test_chat_invalid_provider_returns_error(client, test_user):
    """Test that chat returns error for invalid provider."""
    token = login(client, test_user["email"], test_user["password"])

    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test invalid provider",
            "model_provider": "invalid_provider",
            "model": "some-model",
        },
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
    assert "tidak valid" in data["error"].lower() or "invalid" in data["error"].lower()


# === Test: Default Model Fallback ===
def test_chat_uses_default_model_when_not_specified(client, test_user, monkeypatch):
    """Test that chat uses default models when model not specified."""
    token = login(client, test_user["email"], test_user["password"])

    # Test OpenAI default (should be gpt-4o-mini)
    openai_called = []

    def _fake_openai_create(*args, **kwargs):
        openai_called.append(kwargs.get("model"))
        return _DummyResp("OpenAI default response")

    monkeypatch.setattr(main.client.chat.completions, "create", _fake_openai_create)

    resp1 = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test OpenAI default",
            "model_provider": "openai",
            # No model specified
        },
    )
    assert resp1.status_code == 200
    assert openai_called[0] == "gpt-4o-mini", "OpenAI should default to gpt-4o-mini"

    # Test Gemini default (should be gemini-2.5-flash)
    gemini_called = []

    def _mock_generative_model(model_name, **kwargs):
        gemini_called.append(model_name)
        return _MockGeminiModel(model_name)

    monkeypatch.setattr(genai, "GenerativeModel", _mock_generative_model)

    resp2 = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Test Gemini default",
            "model_provider": "google",
            # No model specified
        },
    )
    assert resp2.status_code == 200
    assert gemini_called[0] == "gemini-2.5-flash", (
        "Gemini should default to gemini-2.5-flash"
    )


# === Test: Session Creation ===
def test_chat_creates_session_when_not_provided(client, test_user, monkeypatch):
    """Test that chat creates a new session when session_id not provided."""
    token = login(client, test_user["email"], test_user["password"])

    def _fake_create(*args, **kwargs):
        return _DummyResp("Session test response")

    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)

    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={
            "message": "Start new chat session",
            "model_provider": "openai",
            "model": "gpt-4o-mini",
        },
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "session_id" in data
    assert isinstance(data["session_id"], int)
    assert data["session_id"] > 0


# === Original Test (kept for backward compatibility) ===
def test_chat_openai_mocked(client, test_user, monkeypatch):
    """Original smoke test - kept for backward compatibility."""
    token = login(client, test_user["email"], test_user["password"])

    def _fake_create(*args, **kwargs):
        return _DummyResp("Jawaban tiruan")

    # Patch the OpenAI client used in main.py
    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)

    resp = client.post(
        "/api/chat",
        headers=auth_headers(token),
        json={"message": "Hello", "model_provider": "openai", "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("answer") == "Jawaban tiruan"
    assert "session_id" in data
