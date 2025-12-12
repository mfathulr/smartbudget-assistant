"""Input validation module for API requests

Provides comprehensive validation for:
- Chat messages (length, content, encoding)
- Transactions (amounts, categories)
- User data (emails, passwords)
- Model parameters
"""

from typing import Optional, Dict, Any, List
import re
from datetime import datetime


class ValidationError(Exception):
    """Custom validation error"""

    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{field}: {message}")


class ChatMessageValidator:
    """Validates chat API messages"""

    MIN_LENGTH = 1
    MAX_LENGTH = 2000
    ALLOWED_LANGUAGES = ["id", "en"]
    ALLOWED_PROVIDERS = ["google", "openai"]

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate chat request data.

        Raises:
            ValidationError: If validation fails

        Returns:
            Dict with validated and sanitized data
        """
        errors = []

        # Message validation
        message = data.get("message", "").strip()
        if not message:
            errors.append(
                ValidationError("message", "Pesan tidak boleh kosong", "EMPTY_MESSAGE")
            )
        elif len(message) < cls.MIN_LENGTH:
            errors.append(
                ValidationError(
                    "message",
                    f"Pesan minimal {cls.MIN_LENGTH} karakter",
                    "TOO_SHORT",
                )
            )
        elif len(message) > cls.MAX_LENGTH:
            errors.append(
                ValidationError(
                    "message",
                    f"Pesan maksimal {cls.MAX_LENGTH} karakter (Anda: {len(message)})",
                    "TOO_LONG",
                )
            )
        else:
            # Sanitize message - remove control characters
            message = cls._sanitize_message(message)

        # Language validation
        lang = data.get("lang", "id").lower()
        if lang not in cls.ALLOWED_LANGUAGES:
            errors.append(
                ValidationError(
                    "lang",
                    f"Bahasa harus: {', '.join(cls.ALLOWED_LANGUAGES)}",
                    "INVALID_LANGUAGE",
                )
            )

        # Provider validation
        provider = data.get("model_provider", "google").lower()
        if provider not in cls.ALLOWED_PROVIDERS:
            errors.append(
                ValidationError(
                    "model_provider",
                    f"Provider harus: {', '.join(cls.ALLOWED_PROVIDERS)}",
                    "INVALID_PROVIDER",
                )
            )

        # Model validation
        model = data.get("model", "").strip()
        if not model:
            errors.append(
                ValidationError("model", "Model tidak boleh kosong", "EMPTY_MODEL")
            )
        elif len(model) > 100:
            errors.append(
                ValidationError("model", "Model terlalu panjang", "MODEL_TOO_LONG")
            )

        # Year/Month validation
        year = cls._validate_year(data.get("year"))
        if isinstance(year, ValidationError):
            errors.append(year)
        else:
            year = year or datetime.now().year

        month = cls._validate_month(data.get("month"))
        if isinstance(month, ValidationError):
            errors.append(month)
        else:
            month = month or datetime.now().month

        if errors:
            raise errors[0]  # Raise first error

        return {
            "message": message,
            "lang": lang,
            "model_provider": provider,
            "model": model,
            "year": year,
            "month": month,
            "session_id": data.get("session_id"),
        }

    @staticmethod
    def _sanitize_message(message: str) -> str:
        """Remove dangerous characters from message"""
        # Remove null bytes
        message = message.replace("\x00", "")

        # Remove other control characters except newline and tab
        message = "".join(ch for ch in message if ord(ch) >= 32 or ch in "\n\t\r")

        return message.strip()

    @staticmethod
    def _validate_year(year: Optional[int]) -> Optional[int]:
        """Validate year parameter"""
        if year is None:
            return None

        try:
            year = int(year)
            if year < 2000 or year > 2100:
                return ValidationError(
                    "year", "Tahun harus antara 2000-2100", "INVALID_YEAR"
                )
            return year
        except (ValueError, TypeError):
            return ValidationError("year", "Tahun harus angka", "INVALID_YEAR")

    @staticmethod
    def _validate_month(month: Optional[int]) -> Optional[int]:
        """Validate month parameter"""
        if month is None:
            return None

        try:
            month = int(month)
            if month < 1 or month > 12:
                return ValidationError("month", "Bulan harus 1-12", "INVALID_MONTH")
            return month
        except (ValueError, TypeError):
            return ValidationError("month", "Bulan harus angka", "INVALID_MONTH")


class TransactionValidator:
    """Validates transaction data"""

    VALID_TYPES = ["income", "expense"]
    VALID_CATEGORIES = [
        "Salary",
        "Bonus",
        "Investment",
        "Food",
        "Transport",
        "Shopping",
        "Entertainment",
        "Utilities",
        "Healthcare",
        "Education",
        "Other",
    ]
    MIN_AMOUNT = 0.01
    MAX_AMOUNT = 999_999_999

    @classmethod
    def validate_transaction(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate transaction data.

        Raises:
            ValidationError: If validation fails
        """
        # Type validation
        tx_type = data.get("type", "").lower()
        if tx_type not in cls.VALID_TYPES:
            raise ValidationError(
                "type", "Tipe harus 'income' atau 'expense'", "INVALID_TYPE"
            )

        # Amount validation
        try:
            amount = float(data.get("amount", 0))
            if amount < cls.MIN_AMOUNT:
                raise ValidationError(
                    "amount",
                    f"Jumlah minimal Rp {cls.MIN_AMOUNT:,.2f}",
                    "AMOUNT_TOO_LOW",
                )
            if amount > cls.MAX_AMOUNT:
                raise ValidationError(
                    "amount",
                    f"Jumlah maksimal Rp {cls.MAX_AMOUNT:,.0f}",
                    "AMOUNT_TOO_HIGH",
                )
        except (ValueError, TypeError):
            raise ValidationError("amount", "Jumlah harus angka", "INVALID_AMOUNT")

        # Category validation
        category = data.get("category", "").strip()
        if not category:
            raise ValidationError(
                "category", "Kategori wajib diisi", "MISSING_CATEGORY"
            )

        if len(category) > 100:
            raise ValidationError(
                "category", "Kategori terlalu panjang", "CATEGORY_TOO_LONG"
            )

        # Description validation
        description = data.get("description", "").strip()
        if len(description) > 500:
            raise ValidationError(
                "description",
                "Deskripsi maksimal 500 karakter",
                "DESCRIPTION_TOO_LONG",
            )

        # Date validation (if provided)
        date = data.get("date")
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise ValidationError(
                    "date",
                    "Format tanggal: YYYY-MM-DD",
                    "INVALID_DATE_FORMAT",
                )

        return {
            "type": tx_type,
            "amount": amount,
            "category": category,
            "description": description,
            "date": date,
            "account": data.get("account", "Cash").strip(),
        }


class EmailValidator:
    """Validates email addresses"""

    EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    @classmethod
    def validate(cls, email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 255:
            return False
        return bool(re.match(cls.EMAIL_REGEX, email))


class PasswordValidator:
    """Validates password strength"""

    MIN_LENGTH = 6
    MIN_UPPERCASE = 0  # Can be optional for UX
    MIN_DIGITS = 0  # Can be optional for UX

    @classmethod
    def validate(cls, password: str):
        """
        Validate password.

        Returns:
            (is_valid, error_message) tuple
        """
        if not password:
            return False, "Password tidak boleh kosong"

        if len(password) < cls.MIN_LENGTH:
            return False, f"Password minimal {cls.MIN_LENGTH} karakter"

        if len(password) > 128:
            return False, "Password maksimal 128 karakter"

        return True, ""

    @classmethod
    def suggest_password(cls, length: int = 12) -> str:
        """Generate a strong password suggestion"""
        import string
        import secrets

        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(characters) for _ in range(length))
