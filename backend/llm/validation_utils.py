"""Enhanced validation utilities for LLM executor

Provides field-specific validation, suggestions, and user-friendly error messages.
"""

from typing import Dict, Any, Optional, List, Tuple
from difflib import get_close_matches
import re
from datetime import datetime

# Valid account list - must match database enum/constants
VALID_ACCOUNTS = {
    "cash": "Cash",
    "bca": "BCA",
    "maybank": "Maybank",
    "seabank": "Seabank",
    "shopeepay": "Shopeepay",
    "gopay": "Gopay",
    "jago": "Jago",
    "isaku": "ISaku",
    "ovo": "Ovo",
    "superbank": "Superbank",
    "blu": "Blu Account (Saving)"
}

VALID_CATEGORIES_BY_TYPE = {
    "income": ["Gaji", "Bonus", "Investment", "Freelance", "Gift", "Refund", "Lainnya"],
    "expense": ["Makan", "Transport", "Hiburan", "Belanja", "Kesehatan", 
                "Investasi", "Utilitas", "Pendidikan", "Lainnya"]
}

# Amount validation rules
AMOUNT_LIMITS = {
    "min": 0,           # Must be > 0
    "max": 100_000_000_000,  # Max 100 trillion
    "large_threshold": 10_000_000,  # Require confirmation above 10 juta
    "suspicious_threshold": 1_000_000_000  # Log suspicious amounts
}

# Name validation rules
NAME_LIMITS = {
    "min_length": 1,
    "max_length": 200
}


class ValidationResult:
    """Enhanced validation result with detailed feedback"""
    
    def __init__(self, success: bool, message: str, code: str, 
                 ask_user: Optional[str] = None, **kwargs):
        self.success = success
        self.message = message
        self.code = code
        self.ask_user = ask_user
        self.details = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to response dict"""
        result = {
            "success": self.success,
            "message": self.message,
            "code": self.code,
        }
        if self.ask_user:
            result["ask_user"] = self.ask_user
        result.update(self.details)
        return result


def suggest_category(description: str, tx_type: str = "expense") -> Optional[str]:
    """
    Suggest category based on description keywords
    
    Args:
        description: Transaction description
        tx_type: "income" or "expense"
        
    Returns:
        Suggested category or None
    """
    if not description:
        return None
    
    keywords = {
        "Makan": ["makan", "resto", "kopi", "cafe", "lunch", "dinner", "warung", "pizza"],
        "Transport": ["gojek", "grab", "bus", "taksi", "kereta", "bensin", "motor"],
        "Hiburan": ["bioskop", "game", "spotify", "netflix", "konser", "tiket"],
        "Belanja": ["supermarket", "mall", "toko", "online", "fashion", "sepatu"],
        "Kesehatan": ["apotek", "dokter", "rumah sakit", "vitamin", "obat"],
        "Investasi": ["saham", "crypto", "reksa dana", "emas", "obligasi"],
        "Utilitas": ["listrik", "air", "internet", "telepon", "gas"],
        "Gaji": ["salary", "gaji", "payroll", "upah"],
    }
    
    desc_lower = description.lower()
    for category, keywords_list in keywords.items():
        if any(kw in desc_lower for kw in keywords_list):
            return category
    
    return None


def find_similar_account(user_input: str, valid_accounts: Dict[str, str] = None) -> Optional[str]:
    """
    Find similar account name with fuzzy matching
    
    Args:
        user_input: User-provided account name
        valid_accounts: Dictionary of valid account names
        
    Returns:
        Most similar account name or None
    """
    if valid_accounts is None:
        valid_accounts = VALID_ACCOUNTS
    
    user_normalized = user_input.lower().strip()
    
    # Exact match (case-insensitive)
    if user_normalized in valid_accounts:
        return valid_accounts[user_normalized]
    
    # Fuzzy match
    matches = get_close_matches(
        user_normalized, 
        valid_accounts.keys(), 
        n=1, 
        cutoff=0.6
    )
    
    return valid_accounts[matches[0]] if matches else None


def validate_account(account_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate account name
    
    Args:
        account_name: Account name to validate
        
    Returns:
        Tuple of (is_valid, normalized_name, error_message)
    """
    if not account_name or not account_name.strip():
        return False, None, "Nama akun harus diisi"
    
    normalized = find_similar_account(account_name)
    if normalized:
        return True, normalized, None
    
    # Not found - suggest alternatives
    similar = get_close_matches(
        account_name.lower(), 
        VALID_ACCOUNTS.keys(), 
        n=3, 
        cutoff=0.4
    )
    
    suggestions = [VALID_ACCOUNTS[s] for s in similar] if similar else []
    valid_list = ", ".join(VALID_ACCOUNTS.values())
    
    error_msg = f"Akun '{account_name}' tidak dikenali"
    if suggestions:
        error_msg += f"\nApakah maksud: {' atau '.join(suggestions)}?"
    error_msg += f"\n\nAkun tersedia:\n{valid_list}"
    
    return False, None, error_msg


def validate_amount(amount: float, field_name: str = "Jumlah", 
                   limits: Dict[str, int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate amount value with rules
    
    Args:
        amount: Amount to validate
        field_name: Field name for error messages
        limits: Custom amount limits
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if limits is None:
        limits = AMOUNT_LIMITS
    
    if amount is None:
        return False, f"{field_name} harus diisi dengan angka"
    
    if amount <= limits["min"]:
        return False, f"{field_name} harus lebih dari Rp 0"
    
    if amount > limits["max"]:
        return False, f"{field_name} maksimal Rp {limits['max']:,.0f}"
    
    return True, None


def validate_category(category: str, tx_type: str = "expense") -> Tuple[bool, Optional[str]]:
    """
    Validate category
    
    Args:
        category: Category name
        tx_type: "income" or "expense"
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not category or not category.strip():
        valid_cats = VALID_CATEGORIES_BY_TYPE.get(tx_type, [])
        return False, (
            f"Kategori harus diisi untuk {tx_type}\n"
            f"Pilihan: {', '.join(valid_cats)}"
        )
    
    return True, None


def validate_name(name: str, field_name: str = "Nama", 
                 limits: Dict[str, int] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate name field
    
    Args:
        name: Name to validate
        field_name: Field name for error messages
        limits: Custom name limits
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if limits is None:
        limits = NAME_LIMITS
    
    if not name or not name.strip():
        return False, f"{field_name} harus diisi"
    
    if len(name) > limits["max_length"]:
        return False, f"{field_name} maksimal {limits['max_length']} karakter"
    
    return True, None


def validate_date(date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate date format
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Tuple of (is_valid, normalized_date, error_message)
    """
    if not date_str or not date_str.strip():
        return True, None, None  # Date is optional
    
    date_str = date_str.strip()
    
    # Try strict YYYY-MM-DD format
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return True, date_str, None
    except ValueError:
        pass
    
    # Try dateparser for natural language
    try:
        import dateparser as dp
        if dp:
            parsed = dp.parse(date_str, locales=["id", "en"])
            if parsed:
                return True, parsed.date().isoformat(), None
    except Exception:
        pass
    
    # Try year-only format
    if re.match(r'^\d{4}$', date_str):
        # Auto-convert to Dec 31 of that year
        normalized = f"{date_str}-12-31"
        return True, normalized, "Dikonversi menjadi 31 Desember"
    
    # Failed to parse
    error = (
        "Format tanggal tidak valid. Coba:\n"
        "- 2025-12-25 (format YYYY-MM-DD)\n"
        "- 25 Desember 2025 (bahasa alami)\n"
        "- 2025 (tahun saja, akan menjadi 31 Desember)"
    )
    return False, None, error


def format_amount_confirmation(amount: float, tx_type: str = "transaksi") -> Tuple[bool, Optional[str]]:
    """
    Check if amount needs confirmation from user
    
    Args:
        amount: Amount value
        tx_type: Type of transaction
        
    Returns:
        Tuple of (needs_confirmation, confirmation_message)
    """
    threshold = AMOUNT_LIMITS["large_threshold"]
    
    if amount > threshold:
        return True, (
            f"⚠️ {tx_type.capitalize()} besar (Rp {amount:,.0f})\n"
            f"Pastikan jumlah benar sebelum melanjutkan"
        )
    
    return False, None


def get_category_suggestion_message(description: str, tx_type: str) -> str:
    """
    Get helpful category suggestion message
    
    Args:
        description: Transaction description
        tx_type: "income" or "expense"
        
    Returns:
        Suggestion message or category choices
    """
    suggested = suggest_category(description, tx_type)
    
    if suggested:
        return f"Kategori yang sesuai: {suggested}"
    
    valid_cats = VALID_CATEGORIES_BY_TYPE.get(tx_type, [])
    return f"Kategori tersedia: {', '.join(valid_cats)}"


# Dictionary for standard error messages
ERROR_MESSAGES = {
    "MISSING_FIELD": "Field '{field}' wajib diisi",
    "INVALID_FORMAT": "Format '{field}' tidak valid",
    "AMOUNT_TOO_SMALL": "Jumlah harus lebih dari Rp 0",
    "AMOUNT_TOO_LARGE": "Jumlah melebihi batas maksimal",
    "ACCOUNT_NOT_FOUND": "Akun '{account}' tidak ditemukan",
    "SAME_ACCOUNT": "Akun asal dan tujuan tidak boleh sama",
    "INSUFFICIENT_BALANCE": "Saldo tidak cukup untuk {action}",
    "DUPLICATE_GOAL": "Target tabungan '{name}' sudah ada",
    "CATEGORY_INVALID": "Kategori '{category}' tidak valid",
    "DATE_INVALID": "Format tanggal tidak valid",
}


def get_error_message(code: str, **kwargs) -> str:
    """
    Get formatted error message
    
    Args:
        code: Error code
        **kwargs: Values to substitute in message
        
    Returns:
        Formatted error message
    """
    template = ERROR_MESSAGES.get(code, f"Kesalahan: {code}")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
