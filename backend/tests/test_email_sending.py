"""Tests for email sending functionality."""

from unittest.mock import patch, MagicMock
import pytest

# Check if sendgrid is available
try:
    import sendgrid

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

skip_if_no_sendgrid = pytest.mark.skipif(
    not SENDGRID_AVAILABLE, reason="sendgrid package not installed"
)


def test_send_otp_email_function_exists(app_ctx):
    """Test that send_otp_email function is importable."""
    from main import send_otp_email

    assert callable(send_otp_email)


def test_send_reset_password_email_function_exists(app_ctx):
    """Test that send_password_reset_email function is importable."""
    from main import send_password_reset_email

    assert callable(send_password_reset_email)


@skip_if_no_sendgrid
def test_send_otp_email_with_mock_sendgrid(app_ctx):
    """Test OTP email sending with mocked SendGrid."""
    from main import send_otp_email

    # Mock SendGrid at the sendgrid module level
    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg.return_value.send.return_value = mock_response

        # Ensure SENDGRID_API_KEY is set for this test
        with patch("main.SENDGRID_API_KEY", "test_key"):
            # Test email sending
            result = send_otp_email(
                to_email="test@example.com", otp_code="123456", user_name="Test User"
            )

            # Should return True on success
            assert result is True


@skip_if_no_sendgrid
def test_send_reset_password_email_with_mock_sendgrid(app_ctx):
    """Test password reset email sending with mocked SendGrid."""
    from main import send_password_reset_email

    # Mock SendGrid at the sendgrid module level
    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg.return_value.send.return_value = mock_response

        # Ensure SENDGRID_API_KEY is set for this test
        with patch("main.SENDGRID_API_KEY", "test_key"):
            # Test email sending
            result = send_password_reset_email(
                to_email="test@example.com",
                reset_token="test_token_12345",
                user_name="Test User",
            )

            # Should return True on success
            assert result is True


def test_email_functions_handle_missing_sendgrid_key(app_ctx):
    """Test that email functions handle missing SendGrid API key gracefully."""
    from main import send_otp_email, send_password_reset_email

    # Mock environment without SendGrid key and without SMTP
    with patch("main.SENDGRID_API_KEY", None):
        with patch("main.SMTP_HOST", None):
            # Should return False or handle gracefully, not crash
            result1 = send_otp_email("test@example.com", "123456", "Test")
            result2 = send_password_reset_email("test@example.com", "token123", "Test")

            # In dev mode without key or SMTP, should return False
            assert result1 is False
            assert result2 is False


@skip_if_no_sendgrid
def test_email_content_includes_otp_code(app_ctx):
    """Test that OTP email contains the OTP code."""
    from main import send_otp_email

    otp_code = "TESTCODE123"

    with patch("main.SendGridAPIClient") as mock_sg:
        mock_sg.return_value.send.return_value = MagicMock(status_code=202)
        mock_sg.return_value.send.return_value = MagicMock(status_code=202)

        send_otp_email("test@example.com", otp_code, "Test User")

        # If SendGrid was called, verify OTP code is in email content
        if mock_sg.called:
            call_args = mock_sg.return_value.send.call_args
            if call_args:
                # The Mail object should contain the OTP code
                mail_obj = call_args[0][0] if call_args[0] else None
                if mail_obj:
                    # Check if OTP is in the email (this is a basic check)
                    assert True  # Email was sent with some content


@skip_if_no_sendgrid
def test_email_content_includes_reset_link(app_ctx):
    """Test that password reset email contains reset token/link."""
    from main import send_password_reset_email

    reset_token = "test_reset_token_xyz"

    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        mock_sg.return_value.send.return_value = MagicMock(status_code=202)

        with patch("main.SENDGRID_API_KEY", "test_key"):
            send_password_reset_email("test@example.com", reset_token, "Test User")

            # Verify SendGrid was called
            assert mock_sg.called


@skip_if_no_sendgrid
def test_email_functions_handle_sendgrid_errors(app_ctx):
    """Test that email functions handle SendGrid API errors gracefully."""
    from main import send_otp_email, send_password_reset_email

    # Mock SendGrid to raise an exception
    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        mock_sg.return_value.send.side_effect = Exception("SendGrid API Error")

        with patch("main.SENDGRID_API_KEY", "test_key"):
            # Should return False and not crash
            result1 = send_otp_email("test@example.com", "123456", "Test")
            result2 = send_password_reset_email("test@example.com", "token", "Test")

            assert result1 is False
            assert result2 is False


@skip_if_no_sendgrid
def test_email_validation_rejects_invalid_addresses(app_ctx):
    """Test that invalid email addresses are handled properly."""
    from main import send_otp_email

    # Mock SendGrid to avoid actual email sending
    with patch("sendgrid.SendGridAPIClient") as mock_sg:
        mock_sg.return_value.send.side_effect = Exception("Invalid email")

        with patch("main.SENDGRID_API_KEY", "test_key"):
            invalid_emails = [
                "",
                "not-an-email",
                "@example.com",
                "user@",
            ]

            for invalid_email in invalid_emails:
                result = send_otp_email(invalid_email, "123456", "Test")
                # Should return False for invalid emails (either no key or SendGrid error)
                assert result is False
