"""Helper functions for financial operations"""

from functools import lru_cache
from database import get_db


def _validate_year_month(user_id, year, month):
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if not isinstance(year, int) or year < 2000 or year > 2100:
        raise ValueError("year must be between 2000 and 2100")
    if not isinstance(month, int) or month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")


def get_month_summary(user_id, year, month):
    """Get income/expense summary for a specific month"""
    _validate_year_month(user_id, year, month)
    db = get_db()
    start_date = f"{year}-{month:02d}-01"

    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    cur = db.execute(
        """
        SELECT
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        WHERE user_id = ? AND date >= ? AND date < ?
        """,
        (user_id, start_date, end_date),
    )
    row = cur.fetchone()

    # Convert Decimal (Postgres) to float for JSON safety
    def _num(v):
        if v is None:
            return 0
        try:
            # For Decimal or str values
            return float(v)
        except Exception:
            return 0

    total_income = _num(row.get("total_income"))
    total_expense = _num(row.get("total_expense"))

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net": total_income - total_expense,
    }


@lru_cache(maxsize=128)
def _cached_financial_context(user_id, year, month):
    """Internal cached function - DO NOT call directly"""
    _validate_year_month(user_id, year, month)
    db = get_db()
    summary = get_month_summary(user_id, year, month)

    # Get recent transactions
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    cur = db.execute(
        """
        SELECT id, date, type, category, description, amount, account
        FROM transactions
        WHERE user_id = ? AND date >= ? AND date < ?
        ORDER BY date DESC
        LIMIT 20
        """,
        (user_id, start_date, end_date),
    )
    rows = cur.fetchall()

    tx_lines = []
    for row in rows:
        amount = float(row["amount"]) if row.get("amount") is not None else 0
        tx_lines.append(
            f"{row['date']}: [{row['type']}] {row.get('category') or '-'} - "
            f"{row.get('description') or ''} Rp {amount:,.0f}"
        )

    if not tx_lines:
        tx_lines.append("No transactions this month.")

    summary_text = (
        f"Summary {year}-{month:02d}: income Rp {summary['total_income']:,.0f}, "
        f"expense Rp {summary['total_expense']:,.0f}, net Rp {summary['net']:,.0f}."
    )
    tx_text = "\n".join(tx_lines)

    return f"{summary_text}\nRecent transactions (latest first):\n{tx_text}\n"


def build_financial_context(user_id, year, month):
    """Build context string with user's financial data for LLM (with caching)"""
    return _cached_financial_context(user_id, year, month)


def invalidate_financial_cache():
    """Invalidate financial context cache after transaction changes"""
    _cached_financial_context.cache_clear()
