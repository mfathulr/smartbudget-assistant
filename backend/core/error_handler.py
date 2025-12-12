"""Error handling middleware and utilities

Provides:
- Centralized error handling for Flask
- Proper error responses with consistent format
- Error logging and monitoring
"""

from functools import wraps
from flask import jsonify, request, g
import traceback
from typing import Callable, Any, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base application error"""

    def __init__(
        self,
        message: str,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: dict = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AppError):
    """Validation error"""

    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details or {},
        )
        if field:
            self.details["field"] = field


class AuthenticationError(AppError):
    """Authentication error"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(AppError):
    """Authorization error"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class NotFoundError(AppError):
    """Resource not found error"""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} tidak ditemukan",
            code="NOT_FOUND",
            status_code=404,
        )


class ConflictError(AppError):
    """Conflict error (e.g., duplicate entry)"""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
        )


class ExternalServiceError(AppError):
    """Error from external service (LLM, email, etc)"""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"Error from {service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
        )


def handle_errors(app):
    """Register error handlers with Flask app"""

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        """Handle application errors"""
        logger.error(
            f"{error.code}: {error.message}",
            status_code=error.status_code,
            **error.details,
        )

        response = {
            "success": False,
            "error": error.message,
            "code": error.code,
        }

        if error.details:
            response["details"] = error.details

        if hasattr(g, "request_id"):
            response["request_id"] = g.request_id

        return jsonify(response), error.status_code

    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 errors"""
        logger.warning("bad_request", error=str(error))
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Bad request",
                    "code": "BAD_REQUEST",
                }
            ),
            400,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Endpoint tidak ditemukan",
                    "code": "NOT_FOUND",
                }
            ),
            404,
        )

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors"""
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Method tidak diizinkan",
                    "code": "METHOD_NOT_ALLOWED",
                }
            ),
            405,
        )

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        logger.error(
            "internal_server_error",
            error=str(error),
            traceback=traceback.format_exc(),
        )

        response = {
            "success": False,
            "error": "Kesalahan server internal. Tim kami telah diberitahu.",
            "code": "INTERNAL_SERVER_ERROR",
        }

        if hasattr(g, "request_id"):
            response["request_id"] = g.request_id

        return jsonify(response), 500

    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle 503 errors"""
        logger.error("service_unavailable", error=str(error))
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Layanan sedang tidak tersedia. Silakan coba lagi nanti.",
                    "code": "SERVICE_UNAVAILABLE",
                }
            ),
            503,
        )


def safe_route(f: Callable) -> Callable:
    """
    Decorator for safe route handling with error handling and logging.

    Usage:
        @app.route("/api/chat", methods=["POST"])
        @require_login
        @safe_route
        def chat_api():
            ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs) -> Tuple[Any, int]:
        try:
            logger.debug(
                f"route_start: {request.method} {request.path}",
                method=request.method,
                path=request.path,
            )

            result = f(*args, **kwargs)

            logger.debug(
                f"route_success: {request.method} {request.path}",
                method=request.method,
                path=request.path,
            )

            return result

        except AppError as e:
            logger.warning(
                f"app_error: {e.code}",
                code=e.code,
                message=e.message,
                status=e.status_code,
            )
            raise

        except Exception as e:
            logger.error(
                f"unhandled_error: {type(e).__name__}",
                error=str(e),
                traceback=traceback.format_exc(),
                path=request.path,
                method=request.method,
            )
            raise AppError(
                message="Kesalahan tidak terduga terjadi",
                code="INTERNAL_ERROR",
                status_code=500,
            )

    return decorated_function


def get_error_response(error: Exception, user_facing: bool = True) -> dict:
    """
    Convert any exception to a proper error response.

    Args:
        error: The exception
        user_facing: If True, hide technical details

    Returns:
        Dict with error response
    """
    if isinstance(error, AppError):
        return {
            "success": False,
            "error": error.message,
            "code": error.code,
            "details": error.details if not user_facing else {},
        }

    # For non-AppError exceptions
    message = (
        "Kesalahan server internal"
        if user_facing
        else f"{type(error).__name__}: {str(error)}"
    )

    return {
        "success": False,
        "error": message,
        "code": "INTERNAL_ERROR",
    }
