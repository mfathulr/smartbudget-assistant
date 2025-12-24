"""Category suggester based on description patterns and user history

Suggests categories for transactions based on:
1. Common keywords in description
2. User's historical category usage
3. Fuzzy matching with confidence scoring
"""

import re
from typing import Optional, List, Tuple
from difflib import get_close_matches


# Common Indonesian keywords to category mapping
CATEGORY_KEYWORDS = {
    # Makanan & Minuman
    "Makanan": [
        "makan",
        "sarapan",
        "lunch",
        "dinner",
        "snack",
        "cemilan",
        "resto",
        "restoran",
        "warung",
        "cafe",
        "kafe",
        "mcd",
        "kfc",
        "pizza",
        "burger",
        "nasi",
        "soto",
        "bakso",
        "mie",
        "ayam",
        "gofood",
        "grabfood",
        "delivery",
        "pesan",
        "food",
    ],
    # Transportasi
    "Transportasi": [
        "transport",
        "bensin",
        "bbm",
        "pertamax",
        "pertalite",
        "parkir",
        "tol",
        "grab",
        "gojek",
        "taxi",
        "taksi",
        "uber",
        "ojek",
        "bus",
        "kereta",
        "commuter",
        "mrt",
        "transjakarta",
        "angkot",
        "ojol",
        "ongkir",
        "kirim",
    ],
    # Belanja
    "Belanja": [
        "belanja",
        "beli",
        "shopping",
        "market",
        "supermarket",
        "minimarket",
        "indomaret",
        "alfamart",
        "hypermart",
        "carrefour",
        "tokopedia",
        "shopee",
        "lazada",
        "bukalapak",
        "blibli",
        "online shop",
        "olshop",
    ],
    # Hiburan
    "Hiburan": [
        "nonton",
        "bioskop",
        "cinema",
        "movie",
        "film",
        "netflix",
        "spotify",
        "youtube",
        "game",
        "gaming",
        "steam",
        "playstation",
        "xbox",
        "karaoke",
        "ktv",
        "concert",
        "konser",
        "tiket",
    ],
    # Kesehatan
    "Kesehatan": [
        "dokter",
        "doctor",
        "rumah sakit",
        "rs",
        "klinik",
        "puskesmas",
        "obat",
        "apotek",
        "pharmacy",
        "vitamin",
        "medical",
        "checkup",
        "periksa",
        "berobat",
        "rawat",
        "therapy",
        "terapi",
    ],
    # Tagihan
    "Tagihan": [
        "listrik",
        "pln",
        "air",
        "pdam",
        "internet",
        "wifi",
        "indihome",
        "telkom",
        "pulsa",
        "token",
        "kredit",
        "cicilan",
        "angsuran",
        "pinjaman",
        "bill",
        "tagihan",
        "bayar",
    ],
    # Pendidikan
    "Pendidikan": [
        "sekolah",
        "kuliah",
        "kampus",
        "spp",
        "ukt",
        "les",
        "kursus",
        "bimbel",
        "buku",
        "alat tulis",
        "atk",
        "pendidikan",
        "education",
    ],
    # Gaji (Income)
    "Gaji": ["gaji", "salary", "upah", "thr", "bonus", "insentif", "komisi"],
    # Investasi (Income)
    "Investasi": [
        "dividen",
        "bunga",
        "interest",
        "saham",
        "reksadana",
        "profit",
        "keuntungan",
        "return",
        "yield",
    ],
}


def suggest_category_from_description(
    description: str, transaction_type: Optional[str] = None
) -> Optional[Tuple[str, float]]:
    """Suggest category based on description keywords

    Args:
        description: Transaction description
        transaction_type: 'income' or 'expense' to filter categories

    Returns:
        Tuple of (category_name, confidence_score) or None if no match
        Confidence: 0.0-1.0 (1.0 = very confident)

    Examples:
        >>> suggest_category_from_description("beli makan siang")
        ("Makanan", 0.95)
        >>> suggest_category_from_description("gofood ayam geprek")
        ("Makanan", 0.90)
        >>> suggest_category_from_description("bensin motor")
        ("Transportasi", 0.85)
    """
    if not description:
        return None

    desc_lower = description.lower()

    # Score each category based on keyword matches
    category_scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        matched_keywords = []

        for keyword in keywords:
            # Exact word match (higher score)
            if re.search(rf"\b{re.escape(keyword)}\b", desc_lower):
                score += 1.0
                matched_keywords.append(keyword)
            # Partial match (lower score)
            elif keyword in desc_lower:
                score += 0.5
                matched_keywords.append(keyword)

        if score > 0:
            # Normalize score based on number of keywords in category
            normalized_score = min(score / len(keywords) * 10, 1.0)
            category_scores[category] = {
                "score": normalized_score,
                "matched": matched_keywords,
            }

    if not category_scores:
        return None

    # Get best match
    best_category = max(category_scores.items(), key=lambda x: x[1]["score"])
    category_name = best_category[0]
    confidence = best_category[1]["score"]

    # Return only if confidence is reasonable (>0.3)
    if confidence > 0.3:
        return (category_name, confidence)

    return None


def suggest_category_from_history(
    user_id: int, description: str, transaction_type: str, db
) -> Optional[Tuple[str, float]]:
    """Suggest category based on user's historical patterns

    Args:
        user_id: User ID
        description: Transaction description
        transaction_type: 'income' or 'expense'
        db: Database connection

    Returns:
        Tuple of (category_name, confidence_score) or None
    """
    if not description:
        return None

    # Get similar descriptions from user's history
    cursor = db.execute(
        """
        SELECT category, description, COUNT(*) as freq
        FROM transactions
        WHERE user_id = %s AND type = %s AND description IS NOT NULL
        GROUP BY category, description
        ORDER BY freq DESC
        LIMIT 50
        """,
        (user_id, transaction_type),
    )

    history = cursor.fetchall()

    if not history:
        return None

    # Find best matching description
    desc_lower = description.lower()
    best_match = None
    best_score = 0.0

    for record in history:
        hist_desc = record["description"].lower() if record["description"] else ""

        # Calculate similarity
        # Simple approach: count common words
        desc_words = set(desc_lower.split())
        hist_words = set(hist_desc.split())

        if not desc_words or not hist_words:
            continue

        common_words = desc_words & hist_words
        similarity = len(common_words) / max(len(desc_words), len(hist_words))

        # Weight by frequency
        frequency_weight = min(record["freq"] / 10, 1.0)
        score = similarity * (0.7 + 0.3 * frequency_weight)

        if score > best_score:
            best_score = score
            best_match = record["category"]

    # Return only if confidence is reasonable (>0.4)
    if best_match and best_score > 0.4:
        return (best_match, best_score)

    return None


def get_category_suggestion(
    description: str, transaction_type: str, user_id: Optional[int] = None, db=None
) -> Optional[dict]:
    """Get category suggestion with multiple methods

    Combines keyword-based and history-based suggestions

    Args:
        description: Transaction description
        transaction_type: 'income' or 'expense'
        user_id: User ID (optional, for history-based)
        db: Database connection (optional, for history-based)

    Returns:
        Dict with suggested category and metadata:
        {
            'category': str,
            'confidence': float (0-1),
            'method': 'keywords' or 'history',
            'message': str (suggestion message for user)
        }
    """
    suggestions = []

    # Method 1: Keyword-based
    keyword_result = suggest_category_from_description(description, transaction_type)
    if keyword_result:
        suggestions.append(
            {
                "category": keyword_result[0],
                "confidence": keyword_result[1],
                "method": "keywords",
            }
        )

    # Method 2: History-based (if user_id and db provided)
    if user_id and db:
        history_result = suggest_category_from_history(
            user_id, description, transaction_type, db
        )
        if history_result:
            suggestions.append(
                {
                    "category": history_result[0],
                    "confidence": history_result[1],
                    "method": "history",
                }
            )

    if not suggestions:
        return None

    # Use highest confidence suggestion
    best_suggestion = max(suggestions, key=lambda x: x["confidence"])

    # Generate message based on confidence
    category = best_suggestion["category"]
    confidence = best_suggestion["confidence"]

    if confidence > 0.8:
        message = f"Saya deteksi ini kategori '{category}'. Benar?"
    elif confidence > 0.6:
        message = f"Sepertinya kategori '{category}'. Atau kategori lain?"
    else:
        message = f"Mungkin kategori '{category}'? Atau yang lain?"

    return {
        "category": category,
        "confidence": confidence,
        "method": best_suggestion["method"],
        "message": message,
    }
