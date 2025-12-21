"""LLM action executor - handles all LLM-initiated financial operations with proper error handling

Uses TransactionService for safe operations with isolation and validation.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Any, Optional
from core import get_logger, TransactionValidator, ValidationError
from database import get_db
from llm.validation_utils import (
    validate_account,
    validate_amount,
    validate_category,
    validate_name,
    validate_date,
    validate_account_with_confirmation,
    validate_date_with_confirmation,
    format_amount_confirmation,
    suggest_category,
    VALID_CATEGORIES_BY_TYPE,
)

try:
    import dateparser
except Exception:
    dateparser = None

logger = get_logger(__name__)


def _parse_amount(val: Optional[str]) -> Optional[float]:
    """
    Best-effort amount parser that tolerates Indonesian formats.
    Examples: "5 juta", "5.000.000", "5000000"
    """
    if val is None:
        return None

    if isinstance(val, (int, float)):
        try:
            return float(val)
        except Exception:
            return None

    s = str(val).lower().strip()

    # Remove currency markers
    s = re.sub(r"(idr|rp)\s*", "", s)

    # Detect multipliers (juta/jt/m = million; ribu/rb/k = thousand)
    multiplier = 1
    suffix_map = {
        "juta": 1_000_000,
        "jt": 1_000_000,
        "m": 1_000_000,
        "ribu": 1_000,
        "rb": 1_000,
        "k": 1_000,
    }

    for suffix, mult in suffix_map.items():
        if s.endswith(suffix):
            multiplier = mult
            s = s[: -len(suffix)].strip()
            break

    # Remove thousands separators and normalize decimal
    s = s.replace(".", "").replace(",", ".")

    try:
        parsed = float(s) * multiplier
        return parsed if parsed > 0 else None
    except Exception:
        return None


def execute_action(
    user_id: int, action_name: str, args: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute LLM action with proper error handling and validation.

    Args:
        user_id: User ID
        action_name: Action name (add_transaction, create_savings_goal, etc)
        args: Action arguments

    Returns:
        Dict with success status and details
    """
    try:
        logger.info(
            "llm_action_started",
            action=action_name,
            user_id=user_id,
            args_keys=list(args.keys()),
        )

        # ADD TRANSACTION (multiple aliases for compatibility)
        if action_name in [
            "add_transaction",
            "record_expense",
            "record_income",
            "add_expense",
            "add_income",
        ]:
            return _execute_add_transaction(user_id, action_name, args)

        # CREATE SAVINGS GOAL
        elif action_name == "create_savings_goal":
            return _execute_create_savings_goal(user_id, args)

        # UPDATE TRANSACTION
        elif action_name == "update_transaction":
            return _execute_update_transaction(user_id, args)

        # DELETE TRANSACTION
        elif action_name == "delete_transaction":
            return _execute_delete_transaction(user_id, args)

        # TRANSFER FUNDS
        elif action_name == "transfer_funds":
            return _execute_transfer_funds(user_id, args)

        else:
            logger.warning("unknown_action", action=action_name, user_id=user_id)
            return {
                "success": False,
                "message": f"Aksi '{action_name}' tidak dikenal",
                "code": "UNKNOWN_ACTION",
            }

    except Exception as e:
        logger.error(
            "llm_action_error",
            action=action_name,
            user_id=user_id,
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Kesalahan saat menjalankan aksi: {str(e)}",
            "code": "EXECUTION_ERROR",
        }


def _execute_add_transaction(
    user_id: int, action_name: str, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute add transaction with validation and isolation"""

    db = get_db()

    # Detect transaction type - MUST be explicit, no defaults
    tx_type = args.get("type")
    if not tx_type:
        if "expense" in action_name or action_name == "record_expense":
            tx_type = "expense"
        elif "income" in action_name or action_name == "record_income":
            tx_type = "income"
        else:
            # No explicit type provided, ask user
            return {
                "success": False,
                "message": "Tipe transaksi harus jelas",
                "code": "MISSING_TYPE",
                "ask_user": "Apakah ini pemasukan (income) atau pengeluaran (expense)?\n"
                "Contoh: 'Catat pemasukan 500k' atau 'Catat pengeluaran 50k'",
                "requires_clarification": True,
            }

    # Parse amount
    amount = _parse_amount(args.get("amount"))
    if amount is None or amount <= 0:
        return {
            "success": False,
            "message": "Jumlah transaksi tidak valid",
            "code": "MISSING_AMOUNT",
            "ask_user": "Berapa jumlahnya?\nContoh: '50 ribu', '500000', '1.5 juta'",
            "requires_clarification": True,
        }

    category = args.get("category", "").strip()
    description = args.get("description", "").strip()
    date = args.get("date")
    account = args.get("account", "").strip()  # NO DEFAULT - ask user if missing

    # Validate required fields BEFORE defaulting
    # Category is required for income/expense
    if not category:
        suggested = suggest_category(description, tx_type) if description else None
        return {
            "success": False,
            "message": "Kategori transaksi harus diisi",
            "code": "MISSING_CATEGORY",
            "ask_user": f"Kategori apa untuk {tx_type} ini?\n"
            f"Pilihan: {', '.join(VALID_CATEGORIES_BY_TYPE.get(tx_type, []))}"
            + (f"\n(Saran: {suggested})" if suggested else ""),
            "requires_clarification": True,
        }

    # Account is required - ask if not provided
    if not account:
        return {
            "success": False,
            "message": "Akun transaksi harus diisi",
            "code": "MISSING_ACCOUNT",
            "ask_user": "Akun mana yang digunakan?\n"
            "Pilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya",
            "requires_clarification": True,
        }

    # Validate account with fuzzy matching and ask for confirmation if needed
    account_result = validate_account_with_confirmation(account)
    if not account_result["success"]:
        return account_result
    
    account = account_result["account"]
    
    # If account parsing was fuzzy-matched, ask for confirmation
    if account_result.get("requires_confirmation"):
        return account_result

    # Date - ask user if not provided (don't default to today)
    if not date:
        return {
            "success": False,
            "message": "Tanggal transaksi harus diisi",
            "code": "MISSING_DATE",
            "ask_user": "Kapan transaksinya?\n"
            "Format: 'hari ini', 'kemarin', '20 desember', 'desember 2025', atau '2025-12-20'",
            "requires_clarification": True,
        }

    # Validate date with natural language and ask for confirmation if needed
    date_result = validate_date_with_confirmation(date)
    if not date_result["success"]:
        return date_result
    
    normalized_date = date_result["date"]
    
    # If date parsing was natural language, ask for confirmation
    if date_result.get("requires_confirmation"):
        return date_result

    # Confirm large amount
    needs_confirm, confirm_msg = format_amount_confirmation(amount, "transaksi")
    if needs_confirm:
        return {
            "success": False,
            "message": "Konfirmasi jumlah besar",
            "code": "CONFIRM_AMOUNT",
            "ask_user": confirm_msg + "\nApakah benar Rp " + f"{amount:,.0f}?",
            "requires_confirmation": True,
        }

    # Validate using TransactionValidator
    try:
        validated = TransactionValidator.validate_transaction(
            {
                "type": tx_type,
                "amount": amount,
                "category": category,
                "description": description,
                "date": normalized_date,
            }
        )
    except ValidationError as ve:
        logger.warning(
            "transaction_validation_failed",
            user_id=user_id,
            field=ve.field,
            message=ve.message,
        )
        return {
            "success": False,
            "message": ve.message,
            "code": ve.code,
            "ask_user": f"Mohon lengkapi: {ve.message}",
            "requires_clarification": True,
        }

    # Execute transaction with direct database operation
    try:
        db.execute(
            """INSERT INTO transactions 
               (user_id, date, type, category, description, amount, account) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                validated["date"],
                validated["type"],
                validated["category"],
                validated["description"],
                validated["amount"],
                account,
            ),
        )
        db.commit()
        result = {
            "success": True,
            "message": f"Transaksi {validated['type']} berhasil dicatat",
            "amount": validated["amount"],
            "category": validated["category"],
        }
    except Exception as e:
        logger.error("transaction_insert_error", user_id=user_id, error=str(e))
        result = {
            "success": False,
            "message": f"Gagal menyimpan transaksi: {str(e)}",
            "code": "INSERT_ERROR",
        }

    return result


def _execute_create_savings_goal(user_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute create savings goal with validation - NO DEFAULTS"""

    db = get_db()
    name = args.get("name", "").strip()
    target_amount = _parse_amount(args.get("target_amount"))
    target_date = args.get("target_date", "").strip()
    description = args.get("description", "").strip()

    # Validation - name required
    if not name:
        return {
            "success": False,
            "message": "Nama target tabungan wajib diisi",
            "code": "MISSING_NAME",
            "ask_user": "Apa nama target tabungan Anda?\nContoh: Umroh, Liburan Bali, Dana Darurat, Laptop Baru",
            "requires_clarification": True,
        }

    # Validate name length
    is_valid, name_error = validate_name(
        name, "Nama target tabungan", {"min_length": 1, "max_length": 100}
    )
    if not is_valid:
        return {
            "success": False,
            "message": name_error,
            "code": "INVALID_NAME",
            "ask_user": name_error,
            "requires_clarification": True,
        }

    # Validate amount required
    if target_amount is None or target_amount <= 0:
        return {
            "success": False,
            "message": "Target jumlah wajib diisi dan harus positif",
            "code": "MISSING_AMOUNT",
            "ask_user": "Berapa target jumlahnya?\nContoh: '100 juta', '50000000', '1.5 miliar'",
            "requires_clarification": True,
        }

    # Validate amount not too large
    is_valid, amount_error = validate_amount(target_amount, "Target jumlah")
    if not is_valid:
        return {
            "success": False,
            "message": amount_error,
            "code": "INVALID_AMOUNT",
            "ask_user": amount_error,
            "requires_clarification": True,
        }

    # Target date: ASK user if not provided (don't default to null)
    if not target_date:
        return {
            "success": False,
            "message": "Target tanggal diperlukan",
            "code": "MISSING_TARGET_DATE",
            "ask_user": "Kapan ingin mencapai target ini?\n"
            "Contoh: '2025-12-31', '31 Desember 2025', atau '2030' (tahun)",
            "requires_clarification": True,
        }

    # Parse target date
    is_valid_date, normalized_date, date_error = validate_date(target_date)
    if not is_valid_date:
        return {
            "success": False,
            "message": date_error,
            "code": "INVALID_DATE",
            "ask_user": date_error,
            "requires_clarification": True,
        }

    try:
        logger.info(
            "create_savings_goal_started",
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            target_date=normalized_date,
        )

        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO savings_goals 
            (user_id, name, target_amount, description, target_date, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (user_id, name, target_amount, description, normalized_date),
        )
        goal_id = cur.fetchone()[0]
        db.commit()

        logger.info(
            "savings_goal_created",
            user_id=user_id,
            goal_id=goal_id,
            name=name,
            target_date=normalized_date,
        )

        # Format date for display
        from datetime import datetime as dt

        try:
            target_dt = dt.strptime(normalized_date, "%Y-%m-%d")
            date_display = target_dt.strftime("%d %B %Y")  # Format: 31 December 2030
        except:
            date_display = normalized_date

        return {
            "success": True,
            "message": f"✅ Target tabungan '{name}' berhasil dibuat",
            "details": {
                "name": name,
                "target_amount": target_amount,
                "target_date": normalized_date,
                "target_date_display": date_display,
                "goal_id": goal_id,
            },
        }

    except Exception as e:
        db.rollback()
        logger.error(
            "create_savings_goal_error",
            user_id=user_id,
            name=name,
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Gagal membuat target tabungan: {str(e)}",
            "code": "GOAL_CREATION_FAILED",
        }


def _execute_update_transaction(user_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute update transaction with validation"""

    transaction_id = args.get("id")

    if not transaction_id:
        return {
            "success": False,
            "message": "ID transaksi wajib diisi",
            "code": "MISSING_ID",
        }

    try:
        db = get_db()
        logger.info(
            "update_transaction_started",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        # Verify transaction belongs to user
        cur = db.cursor()
        cur.execute(
            "SELECT id FROM transactions WHERE id = %s AND user_id = %s",
            (transaction_id, user_id),
        )

        if not cur.fetchone():
            logger.warning(
                "transaction_not_found",
                user_id=user_id,
                transaction_id=transaction_id,
            )
            return {
                "success": False,
                "message": "Transaksi tidak ditemukan atau bukan milik Anda",
                "code": "TRANSACTION_NOT_FOUND",
            }

        # Build update query from provided fields
        update_fields = []
        params = []

        for field in ["date", "type", "category", "description", "amount", "account"]:
            if field in args:
                if field == "amount":
                    value = _parse_amount(args[field])
                    if value is None:
                        return {
                            "success": False,
                            "message": f"Nilai {field} tidak valid",
                            "code": f"INVALID_{field.upper()}",
                        }
                else:
                    value = args[field]

                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            return {
                "success": False,
                "message": "Tidak ada field yang diperbarui",
                "code": "NO_UPDATES",
            }

        params.append(transaction_id)
        params.append(user_id)

        query = (
            f"UPDATE transactions SET {', '.join(update_fields)} "
            "WHERE id = %s AND user_id = %s"
        )

        cur.execute(query, params)
        db.commit()

        logger.info(
            "transaction_updated",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        return {
            "success": True,
            "message": f"✅ Transaksi #{transaction_id} berhasil diperbarui",
            "transaction_id": transaction_id,
        }

    except Exception as e:
        db.rollback()
        logger.error(
            "update_transaction_error",
            user_id=user_id,
            transaction_id=transaction_id,
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Gagal memperbarui transaksi: {str(e)}",
            "code": "UPDATE_FAILED",
        }


def _execute_delete_transaction(user_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute delete transaction with safety checks & confirmation"""

    transaction_id = args.get("id")

    if not transaction_id:
        return {
            "success": False,
            "message": "ID transaksi wajib diisi",
            "code": "MISSING_ID",
            "ask_user": "Transaksi mana yang ingin dihapus? (berikan ID transaksi)",
            "requires_clarification": True,
        }

    try:
        db = get_db()
        logger.info(
            "delete_transaction_started",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        cur = db.cursor()

        # Get transaction details FIRST before deleting
        cur.execute(
            "SELECT id, date, type, category, amount, description, account FROM transactions WHERE id = %s AND user_id = %s",
            (transaction_id, user_id),
        )
        tx_data = cur.fetchone()

        if not tx_data:
            logger.warning(
                "transaction_not_found_for_delete",
                user_id=user_id,
                transaction_id=transaction_id,
            )
            return {
                "success": False,
                "message": "Transaksi tidak ditemukan",
                "code": "TRANSACTION_NOT_FOUND",
            }

        # Require confirmation for large amounts
        if tx_data["amount"] > 5_000_000:
            return {
                "success": False,
                "message": "Transaksi besar - perlu konfirmasi sebelum dihapus",
                "code": "CONFIRM_DELETE",
                "ask_user": f"Yakin ingin menghapus transaksi ini?\n\n"
                f"📅 Tanggal: {tx_data['date']}\n"
                f"💰 Jumlah: Rp {tx_data['amount']:,.0f}\n"
                f"🏷️  Tipe: {tx_data['type']}\n"
                f"📝 Deskripsi: {tx_data['description']}\n\n"
                f"Ketik 'hapus' untuk konfirmasi",
                "requires_confirmation": True,
                "transaction_preview": tx_data,
            }

        # Delete transaction
        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND user_id = %s RETURNING id",
            (transaction_id, user_id),
        )

        deleted = cur.fetchone()
        if not deleted:
            return {
                "success": False,
                "message": "Gagal menghapus transaksi",
                "code": "DELETE_FAILED",
            }

        db.commit()

        logger.info(
            "transaction_deleted",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        return {
            "success": True,
            "message": f"✅ Transaksi #{transaction_id} berhasil dihapus",
            "transaction_id": transaction_id,
        }

    except Exception as e:
        db.rollback()
        logger.error(
            "delete_transaction_error",
            user_id=user_id,
            transaction_id=transaction_id,
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Gagal menghapus transaksi: {str(e)}",
            "code": "DELETE_FAILED",
        }


def _execute_transfer_funds(user_id: int, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute transfer between accounts with validation - NO DEFAULTS"""

    amount = _parse_amount(args.get("amount"))
    from_account = args.get("from_account", "").strip()
    to_account = args.get("to_account", "").strip()
    date = args.get("date")
    description = args.get("description", "").strip()

    # Validate amount
    if not amount or amount <= 0:
        return {
            "success": False,
            "message": "Jumlah transfer harus positif",
            "code": "MISSING_AMOUNT",
            "ask_user": "Berapa jumlah yang akan ditransfer?\nContoh: '100 ribu', '1 juta', '500000'",
            "requires_clarification": True,
        }

    # Validate amount not too large
    is_valid, amount_error = validate_amount(amount, "Jumlah transfer")
    if not is_valid:
        return {
            "success": False,
            "message": amount_error,
            "code": "INVALID_AMOUNT",
            "ask_user": amount_error,
            "requires_clarification": True,
        }

    # From account is required
    if not from_account:
        return {
            "success": False,
            "message": "Akun sumber wajib diisi",
            "code": "MISSING_FROM_ACCOUNT",
            "ask_user": "Dari akun mana?\nPilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya",
            "requires_clarification": True,
        }

    # To account is required
    if not to_account:
        return {
            "success": False,
            "message": "Akun tujuan wajib diisi",
            "code": "MISSING_TO_ACCOUNT",
            "ask_user": "Ke akun mana?\nPilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya",
            "requires_clarification": True,
        }

    # Validate accounts exist & normalize with confirmation
    from_result = validate_account_with_confirmation(from_account)
    if not from_result["success"]:
        return from_result
    
    from_account = from_result["account"]
    if from_result.get("requires_confirmation"):
        return from_result
    
    to_result = validate_account_with_confirmation(to_account)
    if not to_result["success"]:
        return to_result
    
    to_account = to_result["account"]
    if to_result.get("requires_confirmation"):
        return to_result

    # Check different accounts
    if from_account == to_account:
        return {
            "success": False,
            "message": "Akun sumber dan tujuan harus berbeda",
            "code": "SAME_ACCOUNT",
            "ask_user": f"Akun '{from_account}' tidak bisa transfer ke dirinya sendiri.",
            "requires_clarification": True,
        }

    # Check balance (prevent negative balance)
    db = get_db()
    cur_balance = db.execute(
        """SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount 
                                    WHEN type='expense' THEN -amount 
                                    ELSE 0 END), 0) as balance
           FROM transactions WHERE user_id = %s AND account = %s""",
        (user_id, from_account),
    ).fetchone()["balance"]

    if amount > cur_balance:
        return {
            "success": False,
            "message": "Saldo tidak cukup",
            "code": "INSUFFICIENT_BALANCE",
            "ask_user": f"Saldo {from_account}: Rp {cur_balance:,.0f}\n"
            f"Tidak cukup untuk transfer Rp {amount:,.0f}\n"
            f"Kurang: Rp {amount - cur_balance:,.0f}",
            "requires_clarification": True,
            "available_balance": cur_balance,
            "required_amount": amount,
            "shortfall": amount - cur_balance,
        }

    # Date: ask if not provided
    if not date:
        return {
            "success": False,
            "message": "Tanggal transfer harus diisi",
            "code": "MISSING_DATE",
            "ask_user": "Kapan transfernya?\nFormat: 'hari ini', 'kemarin', '20 desember', atau '2025-12-20'",
            "requires_clarification": True,
        }

    # Validate & parse date with confirmation
    date_result = validate_date_with_confirmation(date)
    if not date_result["success"]:
        return date_result
    
    normalized_date = date_result["date"]
    if date_result.get("requires_confirmation"):
        return date_result

    # Description: ask if not provided
    if not description:
        return {
            "success": False,
            "message": "Deskripsi transfer harus diisi",
            "code": "MISSING_DESCRIPTION",
            "ask_user": "Apa tujuan/alasan transfer ini?",
            "requires_clarification": True,
        }

    # Confirm large transfers
    needs_confirm, confirm_msg = format_amount_confirmation(amount, "transfer")
    if needs_confirm:
        return {
            "success": False,
            "message": "Transfer besar - perlu konfirmasi",
            "code": "CONFIRM_TRANSFER",
            "ask_user": f"{confirm_msg}\n\nTransfer dari {from_account} ke {to_account}\nJumlah: Rp {amount:,.0f}",
            "requires_confirmation": True,
            "transfer_preview": {
                "amount": amount,
                "from": from_account,
                "to": to_account,
                "date": normalized_date,
                "description": description,
            },
        }

    try:
        db = get_db()
        logger.info(
            "transfer_started",
            user_id=user_id,
            from_account=from_account,
            to_account=to_account,
            amount=amount,
        )

        # Insert debit transaction from source account
        db.execute(
            """INSERT INTO transactions 
               (user_id, date, type, category, description, amount, account) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                normalized_date,
                "expense",
                "Transfer",
                f"Transfer to {to_account}: {description}",
                amount,
                from_account,
            ),
        )

        # Insert credit transaction to target account
        db.execute(
            """INSERT INTO transactions 
               (user_id, date, type, category, description, amount, account) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                normalized_date,
                "income",
                "Transfer",
                f"Transfer from {from_account}: {description}",
                amount,
                to_account,
            ),
        )

        db.commit()

        logger.info(
            "transfer_completed",
            user_id=user_id,
            from_account=from_account,
            to_account=to_account,
            amount=amount,
        )

        return {
            "success": True,
            "message": f"✅ Transfer Rp {amount:,.0f} dari {from_account} ke {to_account} berhasil",
            "details": {
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount,
                "date": normalized_date,
                "description": description,
                "balance_from": cur_balance - amount,
            },
        }

    except Exception as e:
        logger.error(
            "transfer_error",
            user_id=user_id,
            from_account=from_account,
            to_account=to_account,
            error=str(e),
        )
        return {
            "success": False,
            "message": f"Gagal melakukan transfer: {str(e)}",
            "code": "TRANSFER_FAILED",
        }
