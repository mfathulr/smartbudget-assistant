"""Enhanced validation utilities for LLM executor

Provides field-specific validation, suggestions, and user-friendly error messages.
"""

from typing import Dict, Any, Optional, List, Tuple
from difflib import get_close_matches
import re
from datetime import datetime, timedelta

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
    "blu": "Blu Account (Saving)",
}

# Common bank name mappings for fuzzy matching
COMMON_ACCOUNT_ALIASES = {
    # BCA variations
    "bca": "BCA",
    "bank bca": "BCA",
    "bank central asia": "BCA",
    "bca transfer": "BCA",
    
    # Maybank variations
    "maybank": "Maybank",
    "bank maybank": "Maybank",
    "maybank 2u": "Maybank",
    "maybank malaysia": "Maybank",
    
    # Seabank variations
    "seabank": "Seabank",
    "sea bank": "Seabank",
    "bank sea": "Seabank",
    
    # E-wallet variations
    "gopay": "Gopay",
    "go-pay": "Gopay",
    "google pay": "Gopay",
    "shopeepay": "Shopeepay",
    "shopee pay": "Shopeepay",
    "shopee": "Shopeepay",
    "ovo": "Ovo",
    "ovo pay": "Ovo",
    
    # Jago variations
    "jago": "Jago",
    "bank jago": "Jago",
    
    # Others
    "isaku": "ISaku",
    "i-saku": "ISaku",
    "superbank": "Superbank",
    "blu": "Blu Account (Saving)",
    "blu account": "Blu Account (Saving)",
    "cash": "Cash",
    "tunai": "Cash",
}

VALID_CATEGORIES_BY_TYPE = {
    "income": ["Gaji", "Bonus", "Investment", "Freelance", "Gift", "Refund", "Lainnya"],
    "expense": [
        "Makan",
        "Transport",
        "Hiburan",
        "Belanja",
        "Kesehatan",
        "Investasi",
        "Utilitas",
        "Pendidikan",
        "Lainnya",
    ],
}

# Amount validation rules
AMOUNT_LIMITS = {
    "min": 0,  # Must be > 0
    "max": 100_000_000_000,  # Max 100 trillion
    "large_threshold": 10_000_000,  # Require confirmation above 10 juta
    "suspicious_threshold": 1_000_000_000,  # Log suspicious amounts
}

# Name validation rules
NAME_LIMITS = {"min_length": 1, "max_length": 200}


class ValidationResult:
    """Enhanced validation result with detailed feedback"""

    def __init__(
        self,
        success: bool,
        message: str,
        code: str,
        ask_user: Optional[str] = None,
        **kwargs,
    ):
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
        "Makan": [
            "makan",
            "resto",
            "kopi",
            "cafe",
            "lunch",
            "dinner",
            "warung",
            "pizza",
        ],
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


def find_similar_account(
    user_input: str, valid_accounts: Dict[str, str] = None
) -> Optional[str]:
    """
    Find similar account name with advanced fuzzy matching

    Args:
        user_input: User-provided account name
        valid_accounts: Dictionary of valid account names (unused - uses COMMON_ACCOUNT_ALIASES)

    Returns:
        Most similar account name or None
    """
    if not user_input:
        return None

    user_normalized = user_input.lower().strip()

    # Check exact match in aliases first (includes common names like "bank central asia")
    if user_normalized in COMMON_ACCOUNT_ALIASES:
        return COMMON_ACCOUNT_ALIASES[user_normalized]

    # Check exact match in main dict
    if user_normalized in VALID_ACCOUNTS:
        return VALID_ACCOUNTS[user_normalized]

    # Fuzzy match against aliases (higher priority for common names)
    alias_matches = get_close_matches(
        user_normalized, COMMON_ACCOUNT_ALIASES.keys(), n=1, cutoff=0.65
    )
    if alias_matches:
        return COMMON_ACCOUNT_ALIASES[alias_matches[0]]

    # Fuzzy match against main dict (fallback)
    dict_matches = get_close_matches(
        user_normalized, VALID_ACCOUNTS.keys(), n=1, cutoff=0.6
    )

    return VALID_ACCOUNTS[dict_matches[0]] if dict_matches else None


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
        account_name.lower(), VALID_ACCOUNTS.keys(), n=3, cutoff=0.4
    )

    suggestions = [VALID_ACCOUNTS[s] for s in similar] if similar else []
    valid_list = ", ".join(VALID_ACCOUNTS.values())

    error_msg = f"Akun '{account_name}' tidak dikenali"
    if suggestions:
        error_msg += f"\nApakah maksud: {' atau '.join(suggestions)}?"
    error_msg += f"\n\nAkun tersedia:\n{valid_list}"

    return False, None, error_msg


def validate_amount(
    amount: float, field_name: str = "Jumlah", limits: Dict[str, int] = None
) -> Tuple[bool, Optional[str]]:
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


def validate_category(
    category: str, tx_type: str = "expense"
) -> Tuple[bool, Optional[str]]:
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
            f"Kategori harus diisi untuk {tx_type}\nPilihan: {', '.join(valid_cats)}"
        )

    return True, None


def validate_name(
    name: str, field_name: str = "Nama", limits: Dict[str, int] = None
) -> Tuple[bool, Optional[str]]:
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


def parse_natural_date(date_str: str) -> Optional[str]:
    """
    Parse Indonesian natural language dates
    
    Args:
        date_str: Natural language date string
        
    Returns:
        Normalized date in YYYY-MM-DD format or None
    """
    if not date_str:
        return None
    
    date_str = date_str.lower().strip()
    today = datetime.now().date()
    
    # Exact matches for common terms
    natural_dates = {
        "hari ini": today,
        "today": today,
        "sekarang": today,
        "kemarin": today - timedelta(days=1),
        "yesterday": today - timedelta(days=1),
        "besok": today + timedelta(days=1),
        "tomorrow": today + timedelta(days=1),
        "minggu depan": today + timedelta(days=7),
        "next week": today + timedelta(days=7),
        "minggu lalu": today - timedelta(days=7),
        "last week": today - timedelta(days=7),
        "bulan depan": (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
        "next month": (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
        "bulan lalu": (today.replace(day=1) - timedelta(days=1)).replace(day=1),
        "last month": (today.replace(day=1) - timedelta(days=1)).replace(day=1),
        "tahun depan": today.replace(year=today.year + 1),
        "next year": today.replace(year=today.year + 1),
        "tahun lalu": today.replace(year=today.year - 1),
        "last year": today.replace(year=today.year - 1),
    }
    
    if date_str in natural_dates:
        return natural_dates[date_str].isoformat()
    
    # Month mappings (Indonesian)
    months_id = {
        "januari": 1, "januari": 1, "jan": 1,
        "februari": 2, "feb": 2,
        "maret": 3, "mar": 3,
        "april": 4, "apr": 4,
        "mei": 5,
        "juni": 6, "jun": 6,
        "juli": 7, "jul": 7,
        "agustus": 8, "agt": 8, "aug": 8,
        "september": 9, "sept": 9, "sep": 9,
        "oktober": 10, "okt": 10, "oct": 10,
        "november": 11, "nov": 11,
        "desember": 12, "des": 12, "dec": 12,
    }
    
    # Try pattern: "25 desember 2025" or "25 desember"
    pattern_with_year = r"(\d{1,2})\s+([a-z]+)\s+(\d{4})"
    match = re.match(pattern_with_year, date_str)
    if match:
        day, month_str, year = match.groups()
        month_num = months_id.get(month_str)
        if month_num:
            try:
                dt = datetime(int(year), month_num, int(day)).date()
                return dt.isoformat()
            except ValueError:
                return None
    
    # Try pattern: "25 desember" (use current year)
    pattern_no_year = r"(\d{1,2})\s+([a-z]+)$"
    match = re.match(pattern_no_year, date_str)
    if match:
        day, month_str = match.groups()
        month_num = months_id.get(month_str)
        if month_num:
            try:
                dt = datetime(today.year, month_num, int(day)).date()
                # If date in past, use next year
                if dt < today:
                    dt = dt.replace(year=dt.year + 1)
                return dt.isoformat()
            except ValueError:
                return None
    
    return None


def validate_date(date_str: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate date format with Indonesian natural language support

    Args:
        date_str: Date string to validate

    Returns:
        Tuple of (is_valid, normalized_date, error_message)
    """
    if not date_str or not date_str.strip():
        return True, None, None  # Date is optional

    date_str = date_str.strip()

    # Try natural language first (Indonesian)
    natural_result = parse_natural_date(date_str)
    if natural_result:
        return True, natural_result, None

    # Try strict YYYY-MM-DD format
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return True, date_str, None
    except ValueError:
        pass

    # Try dateparser for other formats
    try:
        import dateparser as dp

        if dp:
            parsed = dp.parse(date_str, locales=["id", "en"])
            if parsed:
                return True, parsed.date().isoformat(), None
    except Exception:
        pass

    # Try year-only format
    if re.match(r"^\d{4}$", date_str):
        # Auto-convert to Dec 31 of that year
        normalized = f"{date_str}-12-31"
        return True, normalized, "Dikonversi menjadi 31 Desember"

    # Failed to parse
    error = (
        "Format tanggal tidak valid. Coba:\n"
        "- Bahasa alami: 'hari ini', 'kemarin', 'bulan depan', 'tahun depan'\n"
        "- Format lengkap: '25 desember 2025' atau '25 desember'\n"
        "- Format YYYY-MM-DD: '2025-12-25'\n"
        "- Tahun saja: '2025' (akan menjadi 31 Desember)"
    )
    return False, None, error


def format_amount_confirmation(
    amount: float, tx_type: str = "transaksi"
) -> Tuple[bool, Optional[str]]:
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


def format_confirmation_request(
    field_name: str,
    parsed_value: str,
    original_input: str,
    field_type: str = "field"
) -> Dict[str, Any]:
    """
    Format a confirmation request when parsing is ambiguous
    
    Args:
        field_name: Name of field (e.g., "Tanggal", "Akun")
        parsed_value: Parsed/normalized value
        original_input: Original user input
        field_type: Type of field (date, account, etc)
        
    Returns:
        Dictionary with confirmation message and details
    """
    messages = {
        "date": f"Saya interpretasi tanggal '{original_input}' menjadi {parsed_value}.\nBenar?",
        "account": f"Saya interpretasi akun '{original_input}' menjadi {parsed_value}.\nBenar?",
        "field": f"Saya interpretasi '{original_input}' menjadi {parsed_value}.\nBenar?",
    }
    
    message = messages.get(field_type, messages["field"])
    
    return {
        "requires_confirmation": True,
        "confirmation_message": message,
        "parsed_value": parsed_value,
        "original_input": original_input,
        "field_name": field_name,
        "ask_user": message + "\nRespons dengan 'ya' atau 'tidak'",
    }


def validate_account_with_confirmation(account_name: str) -> Dict[str, Any]:
    """
    Validate account and ask for confirmation if ambiguous
    
    Args:
        account_name: Account name to validate
        
    Returns:
        Dictionary with validation result and optional confirmation request
    """
    if not account_name or not account_name.strip():
        return {
            "success": False,
            "code": "MISSING_ACCOUNT",
            "message": "Nama akun harus diisi",
            "ask_user": "Dari akun mana?\nPilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya",
        }
    
    account_name = account_name.strip()
    normalized = find_similar_account(account_name)
    
    if normalized:
        # If input is exact match, no confirmation needed
        if account_name.lower() in VALID_ACCOUNTS or account_name.lower() in COMMON_ACCOUNT_ALIASES:
            return {
                "success": True,
                "account": normalized,
                "requires_confirmation": False,
            }
        
        # If fuzzy matched, ask for confirmation
        return format_confirmation_request(
            "Akun", normalized, account_name, "account"
        ) | {"success": True, "account": normalized}
    
    # Not found - suggest alternatives
    similar = get_close_matches(
        account_name.lower(), list(COMMON_ACCOUNT_ALIASES.keys()), n=3, cutoff=0.4
    )
    
    suggestions = [COMMON_ACCOUNT_ALIASES[s] for s in similar] if similar else []
    valid_list = ", ".join(VALID_ACCOUNTS.values())
    
    error_msg = f"Akun '{account_name}' tidak dikenali"
    if suggestions:
        error_msg += f"\nApakah maksud: {' atau '.join(suggestions)}?"
    error_msg += f"\n\nAkun tersedia:\n{valid_list}"
    
    return {
        "success": False,
        "code": "INVALID_ACCOUNT",
        "message": error_msg,
        "ask_user": error_msg,
        "suggestions": suggestions,
    }


def validate_date_with_confirmation(date_str: str) -> Dict[str, Any]:
    """
    Validate date and ask for confirmation if natural language was parsed
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Dictionary with validation result and optional confirmation request
    """
    if not date_str or not date_str.strip():
        return {
            "success": True,
            "date": None,
            "requires_confirmation": False,
        }
    
    date_str = date_str.strip()
    
    # Check if it's a natural language term (exact match)
    natural_terms = [
        "hari ini", "today", "sekarang", "kemarin", "yesterday", "besok", "tomorrow",
        "minggu depan", "next week", "minggu lalu", "last week",
        "bulan depan", "next month", "bulan lalu", "last month",
        "tahun depan", "next year", "tahun lalu", "last year"
    ]
    
    is_natural = date_str.lower() in natural_terms
    
    is_valid, normalized_date, error_msg = validate_date(date_str)
    
    if not is_valid:
        return {
            "success": False,
            "code": "INVALID_DATE",
            "message": error_msg,
            "ask_user": error_msg,
        }
    
    # If natural language or fuzzy parsed, ask for confirmation
    if is_natural or (normalized_date != date_str and date_str not in ["2025-12-31", "2025"]):
        # Format the date nicely for confirmation
        try:
            dt = datetime.fromisoformat(normalized_date)
            formatted = dt.strftime("%A, %d %B %Y")
        except:
            formatted = normalized_date
        
        return format_confirmation_request(
            "Tanggal", formatted, date_str, "date"
        ) | {"success": True, "date": normalized_date}
    
    return {
        "success": True,
        "date": normalized_date,
        "requires_confirmation": False,
    }
