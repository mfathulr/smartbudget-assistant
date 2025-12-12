"""Core Infrastructure Package

Centralized utilities for logging, error handling, validation, and embeddings.

Modules:
- logger: Structured logging configuration
- error_handler: Error handling middleware
- validators: Input validation utilities
- embeddings: Semantic embedding utilities
"""

from .logger import get_logger
from .error_handler import handle_errors
from .validators import TransactionValidator, ValidationError
from .embeddings import (
    generate_embedding,
    ensure_log_embeddings,
    semantic_search,
)

__all__ = [
    "get_logger",
    "handle_errors",
    "TransactionValidator",
    "ValidationError",
    "generate_embedding",
    "ensure_log_embeddings",
    "semantic_search",
]
