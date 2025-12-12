"""
Context Data Query Handler
Untuk pertanyaan tentang data user: summary, laporan, statistik, dsb.
Hanya baca data, tidak ada modifikasi.
"""

from typing import Dict, Any


class ContextDataHandler:
    """Handle queries requiring user data context (read-only)"""

    @staticmethod
    def handle(
        query: str,
        user_id: int,
        intent_type: str,
        db,
        year: int,
        month: int,
        language: str = "id",
    ) -> Dict[str, Any]:
        """
        Handle context data query.

        Args:
            query: User query
            user_id: User ID
            intent_type: Type like 'summary', 'report', 'retrieve'
            db: Database connection
            year, month: Time context
            language: Response language

        Returns:
            Dict with response data and metadata
        """

        if intent_type == "summary":
            return ContextDataHandler._handle_summary(
                query, user_id, db, year, month, language
            )
        elif intent_type == "report":
            return ContextDataHandler._handle_report(
                query, user_id, db, year, month, language
            )
        elif intent_type == "retrieve":
            return ContextDataHandler._handle_retrieve(
                query, user_id, db, year, month, language
            )
        else:
            return {
                "success": False,
                "reason": f"Unknown context data intent type: {intent_type}",
            }

    @staticmethod
    def _handle_summary(
        query: str, user_id: int, db, year: int, month: int, language: str
    ) -> Dict[str, Any]:
        """Get financial summary for the period"""
        try:
            # Query total income and expense
            cur = db.execute(
                """
                SELECT 
                    SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
                FROM transactions
                WHERE user_id = ? AND strftime('%Y-%m', date) = ?
                """,
                (user_id, f"{year:04d}-{month:02d}"),
            )
            row = cur.fetchone()

            total_income = row["total_income"] or 0
            total_expense = row["total_expense"] or 0
            net = total_income - total_expense

            if language == "id":
                response = f"""
📊 Ringkasan Keuangan {month}/{year}:
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Total Pemasukan: Rp {total_income:,.0f}
💸 Total Pengeluaran: Rp {total_expense:,.0f}
━━━━━━━━━━━━━━━━━━━━━━━━
📈 Net: Rp {net:,.0f}
"""
            else:
                response = f"""
📊 Financial Summary {month}/{year}:
━━━━━━━━━━━━━━━━━━━━━━━━
💰 Total Income: ${total_income:,.2f}
💸 Total Expense: ${total_expense:,.2f}
━━━━━━━━━━━━━━━━━━━━━━━━
📈 Net: ${net:,.2f}
"""

            return {
                "success": True,
                "response": response,
                "data": {
                    "total_income": total_income,
                    "total_expense": total_expense,
                    "net": net,
                },
                "response_type": "summary",
                "requires_llm_explanation": False,
            }
        except Exception as e:
            return {"success": False, "reason": f"Error fetching summary: {str(e)}"}

    @staticmethod
    def _handle_report(
        query: str, user_id: int, db, year: int, month: int, language: str
    ) -> Dict[str, Any]:
        """Generate financial report by category"""
        try:
            # Get expense by category
            cur = db.execute(
                """
                SELECT category, COUNT(*) as count, SUM(amount) as total
                FROM transactions
                WHERE user_id = ? AND type='expense' AND strftime('%Y-%m', date) = ?
                GROUP BY category
                ORDER BY total DESC
                """,
                (user_id, f"{year:04d}-{month:02d}"),
            )
            expenses = cur.fetchall()

            report_lines = [
                "📋 Laporan Pengeluaran Berdasarkan Kategori:"
                if language == "id"
                else "📋 Expense Report by Category:"
            ]
            report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

            for row in expenses:
                category = row["category"]
                amount = row["total"]
                count = row["count"]
                report_lines.append(
                    f"{category}: Rp {amount:,.0f} ({count}x)"
                    if language == "id"
                    else f"{category}: ${amount:,.2f} ({count}x)"
                )

            response = "\n".join(report_lines)

            return {
                "success": True,
                "response": response,
                "data": {"expenses_by_category": [dict(row) for row in expenses]},
                "response_type": "report",
                "requires_llm_explanation": True,  # Could benefit from LLM analysis
            }
        except Exception as e:
            return {"success": False, "reason": f"Error generating report: {str(e)}"}

    @staticmethod
    def _handle_retrieve(
        query: str, user_id: int, db, year: int, month: int, language: str
    ) -> Dict[str, Any]:
        """Retrieve specific data points"""
        try:
            # Get balance from accounts
            cur = db.execute(
                "SELECT SUM(balance) as total_balance FROM accounts WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            total_balance = row["total_balance"] or 0

            if language == "id":
                response = f"💰 Total Saldo Akun Anda: Rp {total_balance:,.0f}"
            else:
                response = f"💰 Your Total Account Balance: ${total_balance:,.2f}"

            return {
                "success": True,
                "response": response,
                "data": {"total_balance": total_balance},
                "response_type": "retrieve",
                "requires_llm_explanation": False,
            }
        except Exception as e:
            return {"success": False, "reason": f"Error retrieving data: {str(e)}"}
