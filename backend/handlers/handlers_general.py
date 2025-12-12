"""
General Query Handler
Untuk pertanyaan umum: edukasi, definisi, motivasi, dsb.
Tidak butuh akses database, cepat, bisa di-cache.
"""

from typing import Dict, Any


class GeneralQueryHandler:
    """Handle general/educational queries without database access"""

    # FAQ Database - cached responses
    FAQ_DATABASE = {
        "apa itu budget": {
            "id": "Budget adalah rencana keuangan yang menunjukkan estimasi pemasukan dan pengeluaran dalam periode tertentu (bulanan, tahunan, dsb). Fungsinya untuk membantu Anda mengelola uang dengan baik dan mencapai tujuan finansial.",
            "en": "Budget is a financial plan showing estimated income and expenses for a specific period. It helps you manage money wisely and achieve financial goals.",
        },
        "apa itu saving goal": {
            "id": "Saving Goal adalah target menabung Anda. Misalnya, Anda ingin mengumpulkan Rp 5 juta untuk liburan dalam 6 bulan. SmartBudget membantu Anda tracking progress menuju goal tersebut.",
            "en": "Saving Goal is your savings target. For example, wanting to save $1000 for vacation in 6 months. SmartBudget helps track your progress toward the goal.",
        },
        "bagaimana cara menghemat": {
            "id": "Tips menghemat:\n1. Catat semua pengeluaran Anda\n2. Buat budget realitis\n3. Identifikasi pengeluaran tidak penting\n4. Gunakan sistem 50/30/20 (50% kebutuhan, 30% keinginan, 20% tabungan)\n5. Buat saving goal yang terukur",
            "en": "Tips to save:\n1. Track all expenses\n2. Create realistic budget\n3. Identify unnecessary spending\n4. Use 50/30/20 rule\n5. Set measurable savings goals",
        },
        "apa fitur smartbudget": {
            "id": "Fitur SmartBudget:\n- Pencatatan transaksi otomatis\n- Kategorisasi pengeluaran\n- Laporan analitik\n- Saving goal tracker\n- AI financial advisor\n- Image recognition untuk receipt\n- Multi-account management",
            "en": "SmartBudget features:\n- Automatic transaction recording\n- Expense categorization\n- Analytics reports\n- Savings goal tracking\n- AI financial advisor\n- Receipt image recognition\n- Multi-account management",
        },
    }

    # Motivational quotes
    MOTIVATIONAL_QUOTES = [
        "Kunci kesuksesan finansial adalah disiplin dan konsistensi. Mulai dari hal kecil! 💪",
        "Tidak ada yang mustahil jika Anda memulai dengan rencana yang jelas. 🎯",
        "Setiap rupiah yang Anda hemat hari ini adalah investasi untuk masa depan yang lebih baik. 💰",
        "Perjalanan seribu kilometer dimulai dari satu langkah kecil. Mulai sekarang! 🚀",
    ]

    @staticmethod
    def handle(query: str, language: str = "id") -> Dict[str, Any]:
        """
        Handle general query with FAQ or motivational response.

        Returns:
            Dict with keys: success, response, response_type, cached
        """
        query_lower = query.lower().strip()

        # Try to find FAQ match
        for faq_key, faq_content in GeneralQueryHandler.FAQ_DATABASE.items():
            if faq_key in query_lower:
                return {
                    "success": True,
                    "response": faq_content.get(language, faq_content["id"]),
                    "response_type": "faq",
                    "cached": True,
                    "confidence": 0.95,
                }

        # Check if request is for motivation
        if any(
            word in query_lower
            for word in ["motivasi", "inspirasi", "semangat", "motivation", "inspire"]
        ):
            import random

            quote = random.choice(GeneralQueryHandler.MOTIVATIONAL_QUOTES)
            return {
                "success": True,
                "response": quote,
                "response_type": "motivational",
                "cached": True,
                "confidence": 0.9,
            }

        # If no FAQ match, return need_llm response
        return {
            "success": False,
            "response": None,
            "response_type": "need_llm",
            "cached": False,
            "confidence": 0.3,
            "reason": "Query tidak cocok dengan FAQ yang tersedia",
        }

    @staticmethod
    def add_faq(key: str, id_answer: str, en_answer: str) -> None:
        """Add new FAQ entry dynamically"""
        GeneralQueryHandler.FAQ_DATABASE[key.lower()] = {
            "id": id_answer,
            "en": en_answer,
        }
