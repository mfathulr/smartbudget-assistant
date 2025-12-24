"""Configuration for Input Interpreter - Centralized hardcoded values

This module contains all hardcoded values that were previously scattered
throughout the input interpreter and middleware, making it easier to maintain
and update language, thresholds, and patterns.
"""

# =============================================================================
# CONFIDENCE THRESHOLDS FOR FUZZY MATCHING
# =============================================================================
FUZZY_MATCHING_THRESHOLDS = {
    "exact": 1.0,  # Perfect match
    "high": 0.85,  # Fuzzy match > 85%
    "medium": 0.65,  # Fuzzy match 65-85%
    "low": 0.40,  # Fuzzy match 40-65%
}

# =============================================================================
# NATURAL LANGUAGE TERMS FOR DATE PARSING
# =============================================================================
NATURAL_DATE_TERMS = {
    "indonesian": [
        "hari ini",
        "sekarang",
        "kemarin",
        "besok",
        "minggu depan",
        "minggu lalu",
        "bulan depan",
        "bulan lalu",
        "tahun depan",
        "tahun lalu",
    ],
    "english": [
        "today",
        "now",
        "yesterday",
        "tomorrow",
        "next week",
        "last week",
        "next month",
        "last month",
        "next year",
        "last year",
    ],
}

# Flattened list for quick lookup
ALL_NATURAL_DATE_TERMS = (
    NATURAL_DATE_TERMS["indonesian"] + NATURAL_DATE_TERMS["english"]
)

# =============================================================================
# USER CONFIRMATION RESPONSES
# =============================================================================
CONFIRMATION_YES_RESPONSES = [
    "ya",
    "yes",
    "y",
    "benar",
    "iya",
    "yep",
    "yup",
    "ok",
    "oke",
    "okeh",
    "setuju",
    "iyah",
    "betul",
    "betulkah",
]

CONFIRMATION_NO_RESPONSES = [
    "tidak",
    "no",
    "n",
    "tidak setuju",
    "nggak",
    "enggak",
    "salah",
    "nope",
    "nah",
]

# =============================================================================
# CONFIRMATION MESSAGE TEMPLATES BY FIELD TYPE
# =============================================================================
CONFIRMATION_TEMPLATES = {
    "id": {
        "account": "Jadi akun yang Anda maksud adalah **{value}**, benar?",
        "date": "Tanggalnya adalah **{value}**, ya?",
        "category": "Kategorinya **{value}**, setuju?",
        "default": "{field_type.title()} Anda adalah **{value}**, benar?",
    },
    "en": {
        "account": "So the account you mean is **{value}**, right?",
        "date": "The date is **{value}**, yes?",
        "category": "The category is **{value}**, agree?",
        "default": "Your {field_type} is **{value}**, right?",
    },
}

# =============================================================================
# EXPLANATION MESSAGE TEMPLATES
# =============================================================================
EXPLANATION_TEMPLATES = {
    "id": {
        "account": {
            "empty": "Akun belum disebutkan. Coba kasih tahu akun mana yang dipakai ya!",
            "fuzzy_match": "Saya kira '{input}' itu akun {value}. Yuk saya bantu yakinkan!",
            "fuzzy_with_alternatives": "Saya kira '{input}' itu akun {value}. Yuk saya bantu yakinkan!\nKalau bukan, ada pilihan lain: {alternatives}",
            "no_match": "Hmm, '{input}' bukan akun yang aku kenal. Mungkin maksud Anda salah satu dari ini: {valid_options}?",
        },
        "date": {
            "empty": "Tanggal opsional - aku akan pakai hari ini kalau Anda tidak sebutkan.",
            "natural": "Oke, '{input}' itu {formatted}. Pas, kan?",
            "year_only": "Saya pikir '{input}' maksudnya 31 Desember {input}. Betul?",
            "no_match": "Wah, formatnya agak aneh. Coba dengan 'hari ini', '25 desember', '2025-12-25', atau tahunnya aja '2025'!",
        },
        "category": {
            "empty": "Harus pilih kategori dari: {categories}. Mana yang cocok?",
            "fuzzy_match": "Sepertinya '{input}' itu kategori {value}. Sesuai, kan?",
            "fuzzy_with_alternatives": "Sepertinya '{input}' itu kategori {value}. Sesuai, kan?\nKalau tidak, ada juga: {alternatives}",
            "no_match": "Kategori '{input}' belum pernah aku temui. Pilih dari: {valid_options} ya!",
        },
    },
    "en": {
        "account": {
            "empty": "Account not mentioned. Tell me which account you're using, please!",
            "fuzzy_match": "I think '{input}' is the {value} account. Let me confirm!",
            "fuzzy_with_alternatives": "I think '{input}' is the {value} account. Let me confirm!\nIf not, other options: {alternatives}",
            "no_match": "Hmm, '{input}' is not an account I know. Maybe you meant one of these: {valid_options}?",
        },
        "date": {
            "empty": "Date is optional - I'll use today if you don't specify.",
            "natural": "Okay, '{input}' means {formatted}. Correct?",
            "year_only": "I think '{input}' means December 31, {input}. Right?",
            "no_match": "The format looks odd. Try 'today', 'December 25', '2025-12-25', or just the year '2025'!",
        },
        "category": {
            "empty": "Must pick a category from: {categories}. Which fits?",
            "fuzzy_match": "Seems like '{input}' is {value} category. Correct?",
            "fuzzy_with_alternatives": "Seems like '{input}' is {value} category. Correct?\nIf not, there's also: {alternatives}",
            "no_match": "I haven't encountered category '{input}' before. Choose from: {valid_options} please!",
        },
    },
}

# =============================================================================
# CONFIRMATION RESPONSE TEMPLATES
# =============================================================================
CONFIRMATION_RESPONSE_TEMPLATES = {
    "id": {
        "confirmed": "✅ Bagus! {field_type.title()} {value} sudah dikonfirmasi. Lanjut yuk!",
        "rejected": "Oke, gak jadi pakai '{value}'.\nBeritahu saya {field_type} yang benar ya!",
        "rejected_ask": "Berikan {field_type} yang pas untuk {field_name}",
    },
    "en": {
        "confirmed": "✅ Great! {field_type.title()} {value} confirmed. Let's go!",
        "rejected": "Okay, won't use '{value}'.\nTell me the correct {field_type}!",
        "rejected_ask": "Provide the correct {field_type} for {field_name}",
    },
}

# =============================================================================
# ERROR MESSAGE TEMPLATES FOR VALIDATION
# =============================================================================
ERROR_MESSAGE_TEMPLATES = {
    "id": {
        "date_format": "Format tanggalnya belum tepat 🤔",
        "date_ask": "Coba dengan 'hari ini', '25 desember', atau '2025-12-25'!",
        "amount_format": "Jumlahnya harus berupa angka 💰",
        "amount_ask": "Coba lagi dengan angka aja, misal '500000' atau '500 ribu'",
        "type_ask": "Jenis transaksi apa? 🤷",
        "type_message": "Ini pemasukan, pengeluaran, atau transfer? Beritahu saya!",
        "category_ask": "Kategorinya apa? 🏷️",
        "category_message": "Sebutkan kategori transaksi ya. Biar saya bisa bantu track pengeluaran Anda!",
        "amount_bounds": "Jumlahnya masuk akal gak? 🤔",
        "amount_bounds_ask": "Jumlahnya harus positif dan max 1 miliar. Coba lagi yuk!",
    },
    "en": {
        "date_format": "The date format doesn't look right 🤔",
        "date_ask": "Try 'today', 'December 25', or '2025-12-25'!",
        "amount_format": "The amount must be a number 💰",
        "amount_ask": "Try again with just numbers, like '500000' or '500k'",
        "type_ask": "What type of transaction? 🤷",
        "type_message": "Is this income, expense, or transfer? Tell me!",
        "category_ask": "What's the category? 🏷️",
        "category_message": "Specify the transaction category. It helps me track your spending!",
        "amount_bounds": "Does the amount make sense? 🤔",
        "amount_bounds_ask": "Amount must be positive and max 1 billion. Try again!",
    },
}

# =============================================================================
# HELPER FUNCTIONS TO GET CONFIGURATIONS
# =============================================================================


def get_natural_date_terms():
    """Get all natural language date terms"""
    return ALL_NATURAL_DATE_TERMS


def is_confirmation_yes(response: str) -> bool:
    """Check if response is a yes confirmation"""
    return response.lower().strip() in CONFIRMATION_YES_RESPONSES


def is_confirmation_no(response: str) -> bool:
    """Check if response is a no confirmation"""
    return response.lower().strip() in CONFIRMATION_NO_RESPONSES


def get_confirmation_message(field_type: str, value: str, lang: str = "id") -> str:
    """Get confirmation message for a field type"""
    lang = lang if lang in CONFIRMATION_TEMPLATES else "id"
    template = CONFIRMATION_TEMPLATES[lang].get(
        field_type, CONFIRMATION_TEMPLATES[lang]["default"]
    )
    if "{field_type" in template:
        return template.format(field_type=field_type, value=value)
    return template.format(value=value)


def get_explanation(field_type: str, scenario: str, lang: str = "id", **kwargs) -> str:
    """Get explanation message for field interpretation"""
    lang = lang if lang in EXPLANATION_TEMPLATES else "id"
    template = EXPLANATION_TEMPLATES[lang].get(field_type, {}).get(scenario, "")
    if not template:
        return f"Could not interpret {field_type}"
    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"Error formatting message: missing {e}"


def get_error_message(key: str, lang: str = "id", **kwargs) -> str:
    """Get error message by key"""
    lang = lang if lang in ERROR_MESSAGE_TEMPLATES else "id"
    template = ERROR_MESSAGE_TEMPLATES[lang].get(key, "")
    if not template:
        return "An error occurred"
    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError:
        return template


def get_explanation(field_type: str, message_key: str, **kwargs) -> str:
    """
    Get explanation message with variable interpolation

    Args:
        field_type: Type of field (account, date, category)
        message_key: Key of message template (empty, fuzzy_match, no_match, etc)
        **kwargs: Variables to interpolate

    Returns:
        Formatted explanation message
    """
    template = EXPLANATION_TEMPLATES.get(field_type, {}).get(message_key, "")
    if not template:
        return ""

    try:
        return template.format(**kwargs)
    except KeyError as e:
        return f"Error formatting message: missing {e}"
