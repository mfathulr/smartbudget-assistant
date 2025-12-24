"""Unified field parser with confidence scoring for all transaction fields

Handles parsing and validation of:
- Amount (with Indonesian formats)
- Date (natural language)
- Category (with auto-suggestion)
- Account (with fuzzy matching)
- Description (normalization)

Returns confidence scores to help LLM decide when to ask for clarification.
"""

from typing import Optional, Dict, Any, Tuple
import re
from datetime import datetime, timedelta

from .amount_parser import parse_amount, extract_amount_from_message
from .category_suggester import get_category_suggestion
from .validation_utils import (
    parse_natural_date,
    COMMON_ACCOUNT_ALIASES,
    VALID_ACCOUNTS,
)


def parse_field_with_confidence(
    field_name: str, value: Any, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Parse any field with confidence scoring

    Args:
        field_name: Field to parse ('amount', 'date', 'category', 'account', etc)
        value: Raw value from user
        context: Additional context (user_id, db, transaction_type, etc)

    Returns:
        {
            'success': bool,
            'parsed_value': Any,  # Parsed/normalized value
            'confidence': float,  # 0.0-1.0 (1.0 = very confident)
            'needs_confirmation': bool,  # Should ask user?
            'suggestion_message': Optional[str],  # Message to show user
            'alternatives': Optional[List],  # Other possible values
        }
    """
    context = context or {}

    if field_name == "amount":
        return _parse_amount_field(value)
    elif field_name == "date":
        return _parse_date_field(value)
    elif field_name == "category":
        return _parse_category_field(value, context)
    elif field_name == "account":
        return _parse_account_field(value)
    elif field_name == "description":
        return _parse_description_field(value)
    else:
        # Unknown field - return as-is with low confidence
        return {
            "success": True,
            "parsed_value": value,
            "confidence": 0.5,
            "needs_confirmation": True,
            "suggestion_message": None,
            "alternatives": None,
        }


def _parse_amount_field(value: Any) -> Dict[str, Any]:
    """Parse amount with Indonesian format support"""
    if isinstance(value, (int, float)) and value > 0:
        # Already numeric and valid
        return {
            "success": True,
            "parsed_value": float(value),
            "confidence": 1.0,
            "needs_confirmation": False,
            "suggestion_message": None,
            "alternatives": None,
        }

    if isinstance(value, str):
        parsed = parse_amount(value)
        if parsed and parsed > 0:
            return {
                "success": True,
                "parsed_value": parsed,
                "confidence": 0.9,
                "needs_confirmation": False,
                "suggestion_message": f"Rp {parsed:,.0f} ya?",
                "alternatives": None,
            }

    # Unable to parse
    return {
        "success": False,
        "parsed_value": None,
        "confidence": 0.0,
        "needs_confirmation": True,
        "suggestion_message": "Maaf, jumlahnya berapa ya? (contoh: 50rb, 50000, lima puluh ribu)",
        "alternatives": None,
    }


def _parse_date_field(value: Any) -> Dict[str, Any]:
    """Parse date with natural language support"""
    if isinstance(value, str):
        # Try natural date parsing
        parsed_date = parse_natural_date(value)
        if parsed_date:
            confidence = (
                0.95
                if value.lower() in ["hari ini", "today", "kemarin", "yesterday"]
                else 0.85
            )
            return {
                "success": True,
                "parsed_value": parsed_date.strftime("%Y-%m-%d"),
                "confidence": confidence,
                "needs_confirmation": confidence < 0.9,
                "suggestion_message": f"Tanggal {parsed_date.strftime('%d %B %Y')} ya?"
                if confidence < 0.9
                else None,
                "alternatives": None,
            }

        # Try ISO format
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return {
                "success": True,
                "parsed_value": value,
                "confidence": 1.0,
                "needs_confirmation": False,
                "suggestion_message": None,
                "alternatives": None,
            }
        except ValueError:
            pass

    # Use today as fallback (low confidence)
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "success": True,
        "parsed_value": today,
        "confidence": 0.3,
        "needs_confirmation": True,
        "suggestion_message": "Tanggalnya hari ini atau kapan?",
        "alternatives": None,
    }


def _parse_category_field(value: Any, context: Dict[str, Any]) -> Dict[str, Any]:
    """Parse category with auto-suggestion"""
    if not value:
        # Try to suggest from description
        description = context.get("description")
        transaction_type = context.get("transaction_type")
        user_id = context.get("user_id")
        db = context.get("db")

        if description and transaction_type:
            suggestion = get_category_suggestion(
                description, transaction_type, user_id, db
            )
            if suggestion:
                return {
                    "success": True,
                    "parsed_value": suggestion["category"],
                    "confidence": suggestion["confidence"],
                    "needs_confirmation": suggestion["confidence"] < 0.8,
                    "suggestion_message": suggestion["message"],
                    "alternatives": None,
                }

        # No suggestion available
        return {
            "success": False,
            "parsed_value": None,
            "confidence": 0.0,
            "needs_confirmation": True,
            "suggestion_message": "Kategori apa ya? (Makanan, Transport, Belanja, dll)",
            "alternatives": None,
        }

    # Value provided - validate it
    # For now, accept any string (can add validation later)
    return {
        "success": True,
        "parsed_value": value,
        "confidence": 0.9,
        "needs_confirmation": False,
        "suggestion_message": None,
        "alternatives": None,
    }


def _parse_account_field(value: Any) -> Dict[str, Any]:
    """Parse account with fuzzy matching"""
    if not value:
        # Default to Cash with low confidence
        return {
            "success": True,
            "parsed_value": "Cash",
            "confidence": 0.4,
            "needs_confirmation": True,
            "suggestion_message": "Akun Cash ya? Atau akun lain?",
            "alternatives": list(VALID_ACCOUNTS)[:5],
        }

    value_str = str(value).strip()
    value_lower = value_str.lower()

    # Check exact match
    if value_str in VALID_ACCOUNTS:
        return {
            "success": True,
            "parsed_value": value_str,
            "confidence": 1.0,
            "needs_confirmation": False,
            "suggestion_message": None,
            "alternatives": None,
        }

    # Check aliases
    if value_lower in COMMON_ACCOUNT_ALIASES:
        mapped = COMMON_ACCOUNT_ALIASES[value_lower]
        return {
            "success": True,
            "parsed_value": mapped,
            "confidence": 0.95,
            "needs_confirmation": False,
            "suggestion_message": None,
            "alternatives": None,
        }

    # Fuzzy match
    from difflib import get_close_matches

    matches = get_close_matches(value_str, VALID_ACCOUNTS, n=3, cutoff=0.6)

    if matches:
        return {
            "success": True,
            "parsed_value": matches[0],
            "confidence": 0.7,
            "needs_confirmation": True,
            "suggestion_message": f"Maksudnya akun '{matches[0]}'?",
            "alternatives": matches[1:] if len(matches) > 1 else None,
        }

    # No match - use as custom account
    return {
        "success": True,
        "parsed_value": value_str,
        "confidence": 0.5,
        "needs_confirmation": True,
        "suggestion_message": f"Akun baru '{value_str}' ya?",
        "alternatives": None,
    }


def _parse_description_field(value: Any) -> Dict[str, Any]:
    """Parse and normalize description"""
    if not value:
        return {
            "success": True,
            "parsed_value": None,
            "confidence": 1.0,
            "needs_confirmation": False,
            "suggestion_message": None,
            "alternatives": None,
        }

    # Normalize: trim, remove extra spaces
    normalized = " ".join(str(value).split())

    return {
        "success": True,
        "parsed_value": normalized,
        "confidence": 1.0,
        "needs_confirmation": False,
        "suggestion_message": None,
        "alternatives": None,
    }
