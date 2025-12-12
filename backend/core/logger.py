"""Structured logging configuration for SmartBudget

Provides JSON-structured logging for better observability in production.
All logs include: timestamp, level, service, user_id, request_id, and custom context.
"""

import logging
import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


class ContextualJsonFormatter(logging.Formatter):
    """JSON formatter that includes contextual information"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)

        return json.dumps(log_obj, default=str)


class AppLogger:
    """Application logger with structured logging support"""

    _instance = None
    _loggers: Dict[str, logging.Logger] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def configure(cls, name: str = "smartbudget", level: int = logging.INFO):
        """Configure root logger with structured logging"""
        instance = cls()

        if instance._initialized:
            return

        # Create root logger
        root_logger = logging.getLogger(name)
        root_logger.setLevel(level)
        root_logger.propagate = False

        # Remove existing handlers
        root_logger.handlers.clear()

        # Handler 1: JSON to stdout (for production)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(level)

        if jsonlogger:
            formatter = jsonlogger.JsonFormatter(
                fmt="%(timestamp)s %(level)s %(name)s %(message)s",
                timestamp=True,
            )
        else:
            formatter = ContextualJsonFormatter()

        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

        # Handler 2: Plain text to stderr (for debugging)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
        stderr_formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
        )
        stderr_handler.setFormatter(stderr_formatter)
        root_logger.addHandler(stderr_handler)

        instance._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger for a module"""
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
        return cls._loggers[name]


class StructuredLogger:
    """Wrapper for structured logging with common patterns"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def info(self, event: str, **context):
        """Log info with context"""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            "(unknown file)",
            0,
            event,
            (),
            None,
        )
        record.extra_data = context
        self.logger.handle(record)

    def warning(self, event: str, **context):
        """Log warning with context"""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.WARNING,
            "(unknown file)",
            0,
            event,
            (),
            None,
        )
        record.extra_data = context
        self.logger.handle(record)

    def error(self, event: str, exc: Optional[Exception] = None, **context):
        """Log error with context and optional exception"""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.ERROR,
            "(unknown file)",
            0,
            event,
            (),
            exc,
        )
        record.extra_data = context
        self.logger.handle(record)

    def debug(self, event: str, **context):
        """Log debug with context"""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.DEBUG,
            "(unknown file)",
            0,
            event,
            (),
            None,
        )
        record.extra_data = context
        self.logger.handle(record)


# Initialize on module load
AppLogger.configure()


# Export convenience function
def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for a module"""
    return StructuredLogger(AppLogger.get_logger(name))
