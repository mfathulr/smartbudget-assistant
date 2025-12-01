"""Helper functions for financial operations"""

from datetime import date
from database import get_db


def get_month_summary(user_id, year, month):
    """Get income/expense summary for a specific month"""
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


def build_financial_context(user_id, year, month):
    """Build context string with user's financial data for LLM"""
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
    transactions = cur.fetchall()

    # Get savings goals
    cur = db.execute(
        """
        SELECT id, name, target_amount, current_amount, target_date
        FROM savings_goals
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    goals = cur.fetchall()

    context_parts = [
        f"RINGKASAN BULAN {month}/{year}:",
        f"- Pemasukan: Rp {summary['total_income']:,.0f}".replace(",", "."),
        f"- Pengeluaran: Rp {summary['total_expense']:,.0f}".replace(",", "."),
        f"- Net: Rp {summary['net']:,.0f}".replace(",", "."),
        "",
        "TRANSAKSI TERAKHIR:",
    ]

    for tx in transactions:
        context_parts.append(
            f"[ID:{tx['id']}] {tx['date']} | {tx['type'].upper()} | {tx['category']} | "
            f"Rp {tx['amount']:,.0f} | {tx['account']} | {tx['description'][:50]}".replace(
                ",", "."
            )
        )

    if goals:
        context_parts.append("")
        context_parts.append("TARGET TABUNGAN:")
        for g in goals:
            progress = (
                (g["current_amount"] / g["target_amount"] * 100)
                if g["target_amount"] > 0
                else 0
            )
            context_parts.append(
                f"[ID:{g['id']}] {g['name']} | Target: Rp {g['target_amount']:,.0f} | "
                f"Terkumpul: Rp {g['current_amount']:,.0f} ({progress:.1f}%)".replace(
                    ",", "."
                )
            )

    return "\n".join(context_parts)


def execute_transaction_from_llm(user_id, tx_data):
    """Execute a transaction from LLM tool call"""
    print(f"\n{'=' * 60}")
    print("[DEBUG] execute_transaction_from_llm DIPANGGIL")
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] Transaction Data: {tx_data}")

    db = get_db()
    try:
        tx_type = tx_data.get("type")
        amount = float(tx_data.get("amount", 0))
        category = tx_data.get("category", "Lainnya")
        description = tx_data.get("description", "")
        date_str = tx_data.get("date") or date.today().isoformat()
        account_raw = tx_data.get("account", "Cash")

        # Normalisasi account name (case-insensitive mapping)
        account_mapping = {
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
            "blu": "Blu Account (saving)",
            "blu account": "Blu Account (saving)",
        }
        account = account_mapping.get(str(account_raw).lower(), account_raw)

        print(f"[DEBUG] Type: {tx_type}")
        print(f"[DEBUG] Amount: {amount}")
        print(f"[DEBUG] Category: {category}")
        print(f"[DEBUG] Description: {description}")
        print(f"[DEBUG] Date: {date_str}")
        print(f"[DEBUG] Account (raw): {account_raw}")
        print(f"[DEBUG] Account (normalized): {account}")

        # Validasi tipe transaksi
        if not tx_type or tx_type not in ["income", "expense"]:
            print("[DEBUG] ERROR: Tipe transaksi tidak valid atau tidak ada")
            print(f"{'=' * 60}\n")
            return {
                "success": False,
                "message": "need_type",
                "ask_user": "Mohon klarifikasi, apakah ini transaksi pemasukan atau pengeluaran?",
            }

        # Validasi amount
        if not amount or amount <= 0:
            print("[DEBUG] ERROR: Jumlah tidak valid atau tidak ada")
            print(f"{'=' * 60}\n")
            return {
                "success": False,
                "message": "need_amount",
                "ask_user": "Mohon sebutkan jumlah transaksi dalam rupiah.",
            }

        # Validasi kategori wajib untuk income (harus spesifik)
        if tx_type == "income" and (
            not category or category.lower() in ["lainnya", "uncategorized", "umum", ""]
        ):
            print("[DEBUG] ERROR: Kategori wajib untuk pemasukan")
            print(f"{'=' * 60}\n")
            return {
                "success": False,
                "message": "need_category",
                "ask_user": "Mohon sebutkan kategori pemasukan (contoh: Gaji, Bonus, Penjualan, Investasi, dll.)",
            }

        # Validasi kategori untuk expense (boleh auto tapi tidak boleh kosong)
        if tx_type == "expense" and not category:
            print("[DEBUG] ERROR: Kategori diperlukan untuk pengeluaran")
            print(f"{'=' * 60}\n")
            return {
                "success": False,
                "message": "need_category",
                "ask_user": "Mohon sebutkan kategori pengeluaran (contoh: Makan, Transport, Belanja, dll.)",
            }

        print("[DEBUG] Memulai INSERT ke database...")
        db.execute(
            """
            INSERT INTO transactions (user_id, date, type, category, description, amount, account)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, date_str, tx_type, category, description, amount, account),
        )
        db.commit()
        print("[DEBUG] ✅ INSERT berhasil, data ter-commit ke database")
        print(f"{'=' * 60}\n")

        return {
            "success": True,
            "message": f"Transaksi {tx_type} Rp {amount:,.0f} berhasil dicatat".replace(
                ",", "."
            ),
        }
    except Exception as e:
        db.rollback()
        print(f"[DEBUG] ❌ ERROR saat INSERT: {e}")
        print(f"{'=' * 60}\n")
        return {"success": False, "message": f"Gagal mencatat transaksi: {e}"}
