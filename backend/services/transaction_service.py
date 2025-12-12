"""Transaction Service with proper isolation and error handling

Handles all transaction operations with:
- Database transaction isolation (SERIALIZABLE)
- Proper locking to prevent race conditions
- Comprehensive error handling
- Structured logging
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import traceback

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for safe transaction operations with isolation"""

    @staticmethod
    def record_transaction(
        db,
        user_id: int,
        tx_type: str,
        amount: float,
        category: str,
        description: str = "",
        date: Optional[str] = None,
        account: str = "Cash",
    ) -> Dict[str, Any]:
        """
        Record a transaction with full isolation and locking.

        Args:
            db: Database connection
            user_id: User ID
            tx_type: 'income' or 'expense'
            amount: Transaction amount
            category: Category name
            description: Optional description
            date: Optional date (defaults to today)
            account: Account name (defaults to 'Cash')

        Returns:
            Dict with success status and details
        """
        if date is None:
            date = datetime.now(timezone(timedelta(hours=7))).date().isoformat()

        logger.info(
            "transaction_record_started",
            extra={
                "user_id": user_id,
                "type": tx_type,
                "amount": amount,
                "category": category,
                "date": date,
            },
        )

        # Input validation
        validation_error = TransactionService._validate_transaction(
            tx_type, amount, category
        )
        if validation_error:
            logger.warning("transaction_validation_failed", extra=validation_error)
            return {
                "success": False,
                "message": validation_error["reason"],
                "code": validation_error.get("code", "VALIDATION_ERROR"),
            }

        try:
            # Start transaction with SERIALIZABLE isolation
            # This prevents concurrent modifications
            cur = db.cursor()
            cur.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE")

            try:
                # Step 1: Lock account row FOR UPDATE (prevents concurrent modifications)
                cur.execute(
                    """
                    SELECT id, balance FROM accounts 
                    WHERE user_id = %s AND name = %s 
                    FOR UPDATE
                    """,
                    (user_id, account),
                )
                account_row = cur.fetchone()

                if not account_row:
                    cur.execute("ROLLBACK")
                    logger.error(
                        "account_not_found",
                        extra={"user_id": user_id, "account": account},
                    )
                    return {
                        "success": False,
                        "message": f"Akun '{account}' tidak ditemukan",
                        "code": "ACCOUNT_NOT_FOUND",
                    }

                account_id = account_row[0]
                current_balance = float(account_row[1])

                # Step 2: Validate balance for expenses
                if tx_type == "expense":
                    if current_balance < amount:
                        cur.execute("ROLLBACK")
                        logger.warning(
                            "insufficient_balance",
                            extra={
                                "user_id": user_id,
                                "current": current_balance,
                                "requested": amount,
                            },
                        )
                        return {
                            "success": False,
                            "message": f"Saldo tidak cukup. Saldo: Rp {current_balance:,.0f}, Pengeluaran: Rp {amount:,.0f}",
                            "code": "INSUFFICIENT_BALANCE",
                            "current_balance": current_balance,
                            "requested_amount": amount,
                        }

                # Step 3: Insert transaction
                cur.execute(
                    """
                    INSERT INTO transactions 
                    (user_id, account_id, type, amount, category, description, date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, account_id, tx_type, amount, category, description, date),
                )
                transaction_id = cur.fetchone()[0]

                # Step 4: Update account balance
                new_balance = (
                    current_balance + amount
                    if tx_type == "income"
                    else current_balance - amount
                )

                cur.execute(
                    "UPDATE accounts SET balance = %s WHERE id = %s",
                    (new_balance, account_id),
                )

                # Commit transaction
                db.commit()

                logger.info(
                    "transaction_recorded_success",
                    extra={
                        "transaction_id": transaction_id,
                        "user_id": user_id,
                        "new_balance": new_balance,
                    },
                )

                return {
                    "success": True,
                    "message": f"✅ Transaksi {tx_type} Rp {amount:,.0f} berhasil dicatat",
                    "transaction_id": transaction_id,
                    "new_balance": new_balance,
                }

            except Exception as inner_e:
                db.rollback()
                logger.error(
                    "transaction_execution_error",
                    extra={
                        "user_id": user_id,
                        "error": str(inner_e),
                        "traceback": traceback.format_exc(),
                    },
                )
                return {
                    "success": False,
                    "message": f"Gagal mencatat transaksi: {str(inner_e)}",
                    "code": "TRANSACTION_FAILED",
                }

        except Exception as e:
            logger.error(
                "transaction_service_error",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            return {
                "success": False,
                "message": "Kesalahan server saat mencatat transaksi",
                "code": "SERVER_ERROR",
            }

    @staticmethod
    def _validate_transaction(
        tx_type: str, amount: float, category: str
    ) -> Optional[Dict]:
        """Validate transaction inputs"""
        if tx_type not in ["income", "expense"]:
            return {
                "reason": "Tipe transaksi harus 'income' atau 'expense'",
                "code": "INVALID_TYPE",
            }

        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"reason": "Jumlah harus angka positif", "code": "INVALID_AMOUNT"}

        if amount > 999_999_999:
            return {
                "reason": "Jumlah terlalu besar (maks Rp 999 miliar)",
                "code": "AMOUNT_TOO_LARGE",
            }

        if not category or not isinstance(category, str) or len(category.strip()) == 0:
            return {"reason": "Kategori harus diisi", "code": "MISSING_CATEGORY"}

        if len(category) > 100:
            return {"reason": "Kategori terlalu panjang", "code": "CATEGORY_TOO_LONG"}

        return None

    @staticmethod
    def get_account_balance(db, user_id: int, account_name: str) -> Optional[float]:
        """Safely get account balance"""
        try:
            cur = db.cursor()
            cur.execute(
                "SELECT balance FROM accounts WHERE user_id = %s AND name = %s",
                (user_id, account_name),
            )
            result = cur.fetchone()
            return float(result[0]) if result else None
        except Exception as e:
            logger.error(
                "balance_query_error", extra={"user_id": user_id, "error": str(e)}
            )
            return None

    @staticmethod
    def get_monthly_summary(db, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Get monthly income/expense summary with error handling"""
        try:
            cur = db.cursor()
            # Use date range instead of strftime for better index usage
            cur.execute(
                """
                SELECT 
                    SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
                    SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense,
                    COUNT(*) as transaction_count
                FROM transactions
                WHERE user_id = %s 
                  AND date >= %s::date
                  AND date < %s::date
                """,
                (
                    user_id,
                    f"{year:04d}-{month:02d}-01",
                    f"{year:04d}-{month:02d+1:02d}-01"
                    if month < 12
                    else f"{year + 1:04d}-01-01",
                ),
            )
            result = cur.fetchone()

            if result and result[0] is not None:
                total_income = float(result[0])
                total_expense = float(result[1])
                count = result[2]
            else:
                total_income = total_expense = 0
                count = 0

            return {
                "success": True,
                "total_income": total_income,
                "total_expense": total_expense,
                "net": total_income - total_expense,
                "transaction_count": count,
                "month": f"{year:04d}-{month:02d}",
            }

        except Exception as e:
            logger.error(
                "summary_query_error",
                extra={
                    "user_id": user_id,
                    "year": year,
                    "month": month,
                    "error": str(e),
                },
            )
            return {
                "success": False,
                "message": "Gagal mengambil ringkasan transaksi",
                "error": str(e),
            }
