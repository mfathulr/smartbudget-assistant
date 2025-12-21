"""Input Interpreter - Parse and interpret user input with transparency and confirmation

Handles fuzzy matching for all user input types (dates, accounts, amounts, categories, etc)
with explicit confirmation requests when interpretations are ambiguous.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from difflib import get_close_matches
import re

from validation_utils import (
    parse_natural_date,
    find_similar_account,
    COMMON_ACCOUNT_ALIASES,
    VALID_ACCOUNTS,
    VALID_CATEGORIES_BY_TYPE,
)


class MatchConfidence(Enum):
    """Confidence level for fuzzy matching"""
    EXACT = "exact"  # Exact match
    HIGH = "high"  # Fuzzy match > 0.85
    MEDIUM = "medium"  # Fuzzy match 0.65-0.85
    LOW = "low"  # Fuzzy match 0.4-0.65
    NO_MATCH = "no_match"  # No match found


@dataclass
class InterpretationResult:
    """Result of user input interpretation"""
    
    field_type: str  # "account", "date", "category", "amount", etc
    original_input: str  # Original user input
    interpreted_value: Any  # Parsed/normalized value
    confidence: MatchConfidence  # How confident is the interpretation
    needs_confirmation: bool  # Should ask user to confirm
    alternatives: Optional[List[str]] = None  # Alternative interpretations
    explanation: Optional[str] = None  # Human-readable explanation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary response"""
        result = {
            "field_type": self.field_type,
            "original_input": self.original_input,
            "interpreted_value": self.interpreted_value,
            "confidence": self.confidence.value,
            "needs_confirmation": self.needs_confirmation,
        }
        
        if self.alternatives:
            result["alternatives"] = self.alternatives
        if self.explanation:
            result["explanation"] = self.explanation
            
        return result


class InputInterpreter:
    """Interpret user input across all field types"""
    
    def __init__(self):
        """Initialize interpreter with fuzzy matching thresholds"""
        self.THRESHOLDS = {
            "exact": 1.0,
            "high": 0.85,
            "medium": 0.65,
            "low": 0.40,
        }
    
    def interpret_account(self, user_input: str) -> InterpretationResult:
        """
        Interpret account name with fuzzy matching
        
        Args:
            user_input: User-provided account name
            
        Returns:
            InterpretationResult with confidence and alternatives
        """
        if not user_input or not user_input.strip():
            return InterpretationResult(
                field_type="account",
                original_input=user_input,
                interpreted_value=None,
                confidence=MatchConfidence.NO_MATCH,
                needs_confirmation=False,
                explanation="Akun tidak diberikan",
            )
        
        user_input = user_input.strip()
        user_lower = user_input.lower()
        
        # Check exact match in aliases (case-insensitive)
        if user_lower in COMMON_ACCOUNT_ALIASES:
            return InterpretationResult(
                field_type="account",
                original_input=user_input,
                interpreted_value=COMMON_ACCOUNT_ALIASES[user_lower],
                confidence=MatchConfidence.EXACT,
                needs_confirmation=False,
            )
        
        # Check exact match in main dict
        if user_lower in VALID_ACCOUNTS:
            return InterpretationResult(
                field_type="account",
                original_input=user_input,
                interpreted_value=VALID_ACCOUNTS[user_lower],
                confidence=MatchConfidence.EXACT,
                needs_confirmation=False,
            )
        
        # Fuzzy match against aliases (case-insensitive)
        alias_matches = get_close_matches(
            user_lower,
            COMMON_ACCOUNT_ALIASES.keys(),
            n=3,
            cutoff=self.THRESHOLDS["low"]
        )
        
        if alias_matches:
            best_match = alias_matches[0]
            best_value = COMMON_ACCOUNT_ALIASES[best_match]
            
            # Determine confidence level
            match_ratio = self._get_similarity_ratio(user_lower, best_match)
            confidence = self._get_confidence_level(match_ratio)
            
            # Alternatives
            alternatives = [
                COMMON_ACCOUNT_ALIASES[m] for m in alias_matches[1:3]
            ] if len(alias_matches) > 1 else None
            
            return InterpretationResult(
                field_type="account",
                original_input=user_input,
                interpreted_value=best_value,
                confidence=confidence,
                needs_confirmation=confidence != MatchConfidence.EXACT,
                alternatives=alternatives,
                explanation=f"Saya interpretasi '{user_input}' sebagai akun {best_value}"
                           + (f"\nAlternatif: {', '.join(alternatives)}" if alternatives else ""),
            )
        
        # Fuzzy match against main dict (fallback)
        dict_matches = get_close_matches(
            user_lower,
            VALID_ACCOUNTS.keys(),
            n=3,
            cutoff=self.THRESHOLDS["low"]
        )
        
        if dict_matches:
            best_match = dict_matches[0]
            best_value = VALID_ACCOUNTS[best_match]
            
            match_ratio = self._get_similarity_ratio(user_lower, best_match)
            confidence = self._get_confidence_level(match_ratio)
            
            alternatives = [
                VALID_ACCOUNTS[m] for m in dict_matches[1:3]
            ] if len(dict_matches) > 1 else None
            
            return InterpretationResult(
                field_type="account",
                original_input=user_input,
                interpreted_value=best_value,
                confidence=confidence,
                needs_confirmation=confidence != MatchConfidence.EXACT,
                alternatives=alternatives,
                explanation=f"Saya interpretasi '{user_input}' sebagai akun {best_value}"
                           + (f"\nAlternatif: {', '.join(alternatives)}" if alternatives else ""),
            )
        
        # No match
        valid_accounts = list(VALID_ACCOUNTS.values())
        return InterpretationResult(
            field_type="account",
            original_input=user_input,
            interpreted_value=None,
            confidence=MatchConfidence.NO_MATCH,
            needs_confirmation=False,
            explanation=f"Akun '{user_input}' tidak dikenali. "
                       f"Pilihan: {', '.join(valid_accounts)}",
        )
    
    def interpret_date(self, user_input: str) -> InterpretationResult:
        """
        Interpret date string with natural language support
        
        Args:
            user_input: User-provided date string
            
        Returns:
            InterpretationResult with parsed date and confidence
        """
        if not user_input or not user_input.strip():
            return InterpretationResult(
                field_type="date",
                original_input=user_input,
                interpreted_value=None,
                confidence=MatchConfidence.EXACT,
                needs_confirmation=False,
                explanation="Tanggal opsional (jika kosong, gunakan hari ini)",
            )
        
        user_input = user_input.strip()
        
        # Try natural language parsing
        parsed_date = parse_natural_date(user_input)
        
        if parsed_date:
            # Check if input is exact natural language term
            natural_terms = [
                "hari ini", "today", "sekarang", "kemarin", "yesterday",
                "besok", "tomorrow", "minggu depan", "next week",
                "minggu lalu", "last week", "bulan depan", "next month",
                "bulan lalu", "last month", "tahun depan", "next year",
                "tahun lalu", "last year"
            ]
            
            is_natural_term = user_input.lower() in natural_terms
            confidence = MatchConfidence.EXACT if is_natural_term else MatchConfidence.MEDIUM
            
            # Format date for explanation
            try:
                dt = datetime.fromisoformat(parsed_date)
                formatted = dt.strftime("%A, %d %B %Y")
            except:
                formatted = parsed_date
            
            return InterpretationResult(
                field_type="date",
                original_input=user_input,
                interpreted_value=parsed_date,
                confidence=confidence,
                needs_confirmation=not is_natural_term,
                explanation=f"Saya interpretasi '{user_input}' menjadi {formatted}",
            )
        
        # Try strict YYYY-MM-DD format
        try:
            dt = datetime.strptime(user_input, "%Y-%m-%d")
            return InterpretationResult(
                field_type="date",
                original_input=user_input,
                interpreted_value=user_input,
                confidence=MatchConfidence.EXACT,
                needs_confirmation=False,
            )
        except ValueError:
            pass
        
        # Try year-only format
        if re.match(r"^\d{4}$", user_input):
            normalized = f"{user_input}-12-31"
            return InterpretationResult(
                field_type="date",
                original_input=user_input,
                interpreted_value=normalized,
                confidence=MatchConfidence.MEDIUM,
                needs_confirmation=True,
                explanation=f"Saya interpretasi '{user_input}' menjadi 31 Desember {user_input}",
            )
        
        # No match
        return InterpretationResult(
            field_type="date",
            original_input=user_input,
            interpreted_value=None,
            confidence=MatchConfidence.NO_MATCH,
            needs_confirmation=False,
            explanation="Format tanggal tidak valid. "
                       "Coba: 'hari ini', '25 desember', '2025-12-25', atau '2025'",
        )
    
    def interpret_category(self, user_input: str, tx_type: str = "expense") -> InterpretationResult:
        """
        Interpret category with fuzzy matching
        
        Args:
            user_input: User-provided category
            tx_type: Transaction type (income/expense)
            
        Returns:
            InterpretationResult with category match
        """
        if not user_input or not user_input.strip():
            categories = VALID_CATEGORIES_BY_TYPE.get(tx_type, [])
            return InterpretationResult(
                field_type="category",
                original_input=user_input,
                interpreted_value=None,
                confidence=MatchConfidence.NO_MATCH,
                needs_confirmation=False,
                explanation=f"Kategori tersedia: {', '.join(categories)}",
            )
        
        user_input = user_input.strip()
        valid_categories = VALID_CATEGORIES_BY_TYPE.get(tx_type, [])
        
        # Check exact match (case-insensitive)
        for cat in valid_categories:
            if cat.lower() == user_input.lower():
                return InterpretationResult(
                    field_type="category",
                    original_input=user_input,
                    interpreted_value=cat,
                    confidence=MatchConfidence.EXACT,
                    needs_confirmation=False,
                )
        
        # Fuzzy match
        matches = get_close_matches(
            user_input.lower(),
            [c.lower() for c in valid_categories],
            n=3,
            cutoff=self.THRESHOLDS["low"]
        )
        
        if matches:
            # Find original case
            best_match = next(
                (cat for cat in valid_categories if cat.lower() == matches[0]),
                matches[0]
            )
            
            match_ratio = self._get_similarity_ratio(user_input.lower(), matches[0])
            confidence = self._get_confidence_level(match_ratio)
            
            # Alternatives
            alternatives = [
                next((cat for cat in valid_categories if cat.lower() == m), m)
                for m in matches[1:3]
            ] if len(matches) > 1 else None
            
            return InterpretationResult(
                field_type="category",
                original_input=user_input,
                interpreted_value=best_match,
                confidence=confidence,
                needs_confirmation=confidence != MatchConfidence.EXACT,
                alternatives=alternatives,
                explanation=f"Saya interpretasi '{user_input}' sebagai kategori {best_match}"
                           + (f"\nAlternatif: {', '.join(alternatives)}" if alternatives else ""),
            )
        
        # No match
        return InterpretationResult(
            field_type="category",
            original_input=user_input,
            interpreted_value=None,
            confidence=MatchConfidence.NO_MATCH,
            needs_confirmation=False,
            explanation=f"Kategori '{user_input}' tidak dikenali. "
                       f"Pilihan: {', '.join(valid_categories)}",
        )
    
    def format_confirmation_message(self, result: InterpretationResult) -> str:
        """
        Format a user-friendly confirmation message (without technical details)
        
        Args:
            result: InterpretationResult to format
            
        Returns:
            Formatted confirmation message
        """
        if not result.needs_confirmation or not result.interpreted_value:
            return ""
        
        msg = f"Saya interpretasi '{result.original_input}' sebagai "
        
        if result.field_type == "account":
            msg += f"akun **{result.interpreted_value}**"
        elif result.field_type == "date":
            msg += f"tanggal **{result.interpreted_value}**"
        elif result.field_type == "category":
            msg += f"kategori **{result.interpreted_value}**"
        else:
            msg += f"{result.field_type} **{result.interpreted_value}**"
        
        if result.alternatives:
            msg += f"\n\nAlternatif lain: {', '.join(result.alternatives)}"
        
        msg += "\n\nBenar? Respons dengan 'ya' atau 'tidak'"
        
        return msg
    
    def _get_similarity_ratio(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _get_confidence_level(self, ratio: float) -> MatchConfidence:
        """Determine confidence level from similarity ratio"""
        if ratio >= self.THRESHOLDS["exact"]:
            return MatchConfidence.EXACT
        elif ratio >= self.THRESHOLDS["high"]:
            return MatchConfidence.HIGH
        elif ratio >= self.THRESHOLDS["medium"]:
            return MatchConfidence.MEDIUM
        elif ratio >= self.THRESHOLDS["low"]:
            return MatchConfidence.LOW
        return MatchConfidence.NO_MATCH


# Global interpreter instance
_interpreter = None


def get_interpreter() -> InputInterpreter:
    """Get or create global interpreter instance"""
    global _interpreter
    if _interpreter is None:
        _interpreter = InputInterpreter()
    return _interpreter


def interpret_input(field_type: str, user_input: str, **kwargs) -> InterpretationResult:
    """
    Convenience function to interpret any field type
    
    Args:
        field_type: Type of field ("account", "date", "category")
        user_input: User input string
        **kwargs: Additional arguments (e.g., tx_type for category)
        
    Returns:
        InterpretationResult
    """
    interpreter = get_interpreter()
    
    if field_type == "account":
        return interpreter.interpret_account(user_input)
    elif field_type == "date":
        return interpreter.interpret_date(user_input)
    elif field_type == "category":
        tx_type = kwargs.get("tx_type", "expense")
        return interpreter.interpret_category(user_input, tx_type)
    else:
        raise ValueError(f"Unknown field type: {field_type}")
