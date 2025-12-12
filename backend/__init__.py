"""
SmartBudget Backend - Module Index
Quick reference for imports and module organization
"""

# Core Infrastructure
from config import (
    BASE_DIR,
    FLASK_CONFIG,
    GOOGLE_API_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    APP_URL,
    RECAPTCHA_SITE_KEY,
    RECAPTCHA_SECRET_KEY,
)
from database import get_db, close_db, init_db  # Database connection pool
from core import get_logger  # Structured logging

# Business Logic & Services
from services import TransactionService, ConversationStateManager, IntentClassifier

# Pipeline - Chat Orchestration
from pipeline import ChatPipelineManager

# LLM & AI
from llm import execute_action, TOOLS_DEFINITIONS

# Handlers - Query Routing
from handlers import GeneralQueryHandler, ContextDataHandler, InteractionDataHandler

# Authentication & Security
from auth import require_login, require_admin

# Utilities
from financial_context import get_month_summary, build_financial_context
from memory import build_memory_context, log_message, maybe_update_summary
from core import TransactionValidator, ValidationError, handle_errors

# Routes
from routes.memory_routes import memory_bp

__all__ = [
    # Config
    "BASE_DIR",
    "FLASK_CONFIG",
    "GOOGLE_API_KEY",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "APP_URL",
    "RECAPTCHA_SITE_KEY",
    "RECAPTCHA_SECRET_KEY",
    "get_logger",
    # Database
    "get_db",
    "close_db",
    "init_db",
    # Core Infrastructure
    "TransactionValidator",
    "ValidationError",
    "handle_errors",
    # Services
    "TransactionService",
    "ConversationStateManager",
    "IntentClassifier",
    # Pipeline
    "ChatPipelineManager",
    # LLM
    "execute_action",
    "TOOLS_DEFINITIONS",
    # Handlers
    "GeneralQueryHandler",
    "ContextDataHandler",
    "InteractionDataHandler",
    # Auth
    "require_login",
    "require_admin",
    # Utils
    "get_month_summary",
    "build_financial_context",
    "build_memory_context",
    "log_message",
    "maybe_update_summary",
    # Routes
    "memory_bp",
]
