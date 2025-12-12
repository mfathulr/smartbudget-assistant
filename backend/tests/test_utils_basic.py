"""Unit tests for helper utilities in main.py."""

from main import app, get_language, sanitize_for_logging


def test_get_language_prefers_accept_language_header():
    with app.test_request_context(headers={"Accept-Language": "en-US"}):
        assert get_language() == "en"
    with app.test_request_context(headers={"Accept-Language": "id-ID"}):
        assert get_language() == "id"


def test_get_language_falls_back_to_default():
    with app.test_request_context():
        assert get_language() == "id"


def test_sanitize_for_logging_masks_sensitive_fields():
    payload = {
        "email": "user@example.com",
        "password": "secret",
        "token": "abcd",
        "api_key": "123",
        "otp": "8888",
        "nested": {"password": "shouldstay"},
    }
    sanitized = sanitize_for_logging(payload)
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["token"] == "***REDACTED***"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["otp"] == "***REDACTED***"
    assert sanitized["email"] == "user@example.com"
    # ensure nested dict is untouched (function is shallow on purpose)
    assert sanitized["nested"]["password"] == "shouldstay"
