"""Enhanced amount parsing for Indonesian & English number formats

Handles various input formats:
- Indonesian: "50rb", "50k", "5jt", "1.5jt", "50.000", "lima puluh ribu"
- English: "50k", "1.5m", "50,000"
- Standard: "50000", "50000.5"
"""

import re
from typing import Optional, Union


# Indonesian number words mapping
INDONESIAN_NUMBERS = {
    "nol": 0,
    "satu": 1,
    "dua": 2,
    "tiga": 3,
    "empat": 4,
    "lima": 5,
    "enam": 6,
    "tujuh": 7,
    "delapan": 8,
    "sembilan": 9,
    "sepuluh": 10,
    "sebelas": 11,
    "belas": 10,
    "puluh": 10,
    "ratus": 100,
    "ribu": 1000,
    "juta": 1000000,
    "jt": 1000000,
    "milyar": 1000000000,
    "miliar": 1000000000,
}


def parse_amount(text: str) -> Optional[float]:
    """Parse amount from various text formats

    Args:
        text: Input text containing amount

    Returns:
        Parsed amount as float, or None if unable to parse

    Examples:
        >>> parse_amount("50rb")
        50000.0
        >>> parse_amount("1.5jt")
        1500000.0
        >>> parse_amount("lima puluh ribu")
        50000.0
        >>> parse_amount("50k")
        50000.0
        >>> parse_amount("Rp 50.000")
        50000.0
    """
    if not text or not isinstance(text, str):
        return None

    text_lower = text.lower().strip()

    # Try shorthand formats first (most common)
    amount = _parse_shorthand(text_lower)
    if amount is not None:
        return amount

    # Try numeric formats with separators
    amount = _parse_numeric(text_lower)
    if amount is not None:
        return amount

    # Try Indonesian word numbers (least common, most expensive)
    amount = _parse_indonesian_words(text_lower)
    if amount is not None:
        return amount

    return None


def _parse_shorthand(text: str) -> Optional[float]:
    """Parse shorthand formats like 50k, 1.5jt, 2m, 50rb

    Examples:
        50k -> 50000
        1.5jt -> 1500000
        50rb -> 50000
        2m -> 2000000
    """
    # Pattern: number + optional decimal + suffix
    pattern = (
        r"(\d+(?:[.,]\d+)?)\s*(rb|ribu|k|jt|juta|m|million|milyar|miliar|b|billion)?"
    )
    match = re.search(pattern, text)

    if not match:
        return None

    num_str = match.group(1).replace(",", ".")
    suffix = match.group(2) or ""

    try:
        base_num = float(num_str)
    except ValueError:
        return None

    # Apply multiplier based on suffix
    multipliers = {
        "rb": 1000,
        "ribu": 1000,
        "k": 1000,
        "jt": 1000000,
        "juta": 1000000,
        "m": 1000000,
        "million": 1000000,
        "milyar": 1000000000,
        "miliar": 1000000000,
        "b": 1000000000,
        "billion": 1000000000,
    }

    multiplier = multipliers.get(suffix, 1)
    return base_num * multiplier


def _parse_numeric(text: str) -> Optional[float]:
    """Parse numeric formats with separators

    Examples:
        50.000 -> 50000
        50,000 -> 50000
        Rp 50.000 -> 50000
        $ 50,000.50 -> 50000.50
    """
    # Remove currency symbols and spaces
    cleaned = re.sub(r"[rp$€¥£\s]+", "", text, flags=re.IGNORECASE)

    # Check for decimal separator pattern (European: 1.000,50 or American: 1,000.50)
    # European format: dots for thousands, comma for decimal
    if re.search(r"\d+\.\d{3}", cleaned) and "," in cleaned:
        # European: 1.000,50 -> 1000.50
        cleaned = cleaned.replace(".", "").replace(",", ".")
    # American format: commas for thousands, dot for decimal
    elif re.search(r"\d+,\d{3}", cleaned):
        # American: 1,000.50 -> 1000.50
        cleaned = cleaned.replace(",", "")
    # Indonesian format: dots for thousands, no decimal
    elif re.search(r"^\d+(\.\d{3})+$", cleaned):
        # Indonesian: 50.000 -> 50000
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_indonesian_words(text: str) -> Optional[float]:
    """Parse Indonesian number words

    Examples:
        lima puluh ribu -> 50000
        satu juta lima ratus ribu -> 1500000
        dua ratus ribu -> 200000
    """
    # Remove common words
    text = re.sub(r"\b(rupiah|rp)\b", "", text)
    words = text.split()

    if not any(word in INDONESIAN_NUMBERS for word in words):
        return None

    total = 0
    current = 0

    for word in words:
        if word not in INDONESIAN_NUMBERS:
            continue

        num = INDONESIAN_NUMBERS[word]

        if num >= 1000:
            # Multiplier (ribu, juta, etc)
            if current == 0:
                current = 1  # Handle "ribu" without preceding number
            current *= num
            total += current
            current = 0
        elif num >= 10 and num < 100:
            # Puluh or ratus
            if current == 0:
                current = num
            else:
                current *= num
        else:
            # Base numbers (0-9)
            current += num

    total += current
    return float(total) if total > 0 else None


def extract_amount_from_message(message: str) -> Optional[float]:
    """Extract and parse amount from a natural language message

    Args:
        message: User message that might contain an amount

    Returns:
        Parsed amount or None if not found

    Examples:
        >>> extract_amount_from_message("catat pengeluaran 50rb beli makan")
        50000.0
        >>> extract_amount_from_message("transfer 1.5jt dari BCA")
        1500000.0
    """
    # Try to find amount patterns in the message
    # Look for numbers with optional currency and suffixes
    patterns = [
        r"(?:rp\.?\s*)?(\d+(?:[.,]\d+)?)\s*(rb|ribu|k|jt|juta|m|million)",
        r"(?:rp\.?\s*)?(\d+[.,]\d{3}(?:[.,]\d{3})*)",
        r"\b(\d+(?:[.,]\d+)?)\s*(?:rb|ribu|k|jt|juta)\b",
        r"\b(\d{3,})\b",  # At least 3 digits
    ]

    for pattern in patterns:
        match = re.search(pattern, message.lower())
        if match:
            amount = parse_amount(match.group(0))
            if amount and amount > 0:
                return amount

    # Try Indonesian word numbers as last resort
    amount = _parse_indonesian_words(message.lower())
    if amount and amount > 0:
        return amount

    return None
