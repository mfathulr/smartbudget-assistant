"""LLM action executor - handles all LLM-initiated financial operations with proper error handling

Uses TransactionService for safe operations with isolation and validation.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Any, Optional
from core import get_logger, TransactionValidator, ValidationError
from database import get_db

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

    # Detect transaction type
    tx_type = args.get("type")
    if not tx_type:
        if "expense" in action_name or action_name == "record_expense":
            tx_type = "expense"
        elif "income" in action_name or action_name == "record_income":
            tx_type = "income"
        else:
            tx_type = "expense"  # default

    # Parse amount
    amount = _parse_amount(args.get("amount"))
    category = args.get("category", "").strip()
    description = args.get("description", "").strip()
    date = args.get("date")
    account = args.get("account", "Cash").strip()

    # Validate using TransactionValidator
    try:
        validated = TransactionValidator.validate_transaction(
            {
                "type": tx_type,
                "amount": amount,
                "category": category,
                "description": description,
                "date": date or datetime.now().strftime("%Y-%m-%d"),
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
    """Execute create savings goal with validation"""

    db = get_db()
    name = args.get("name", "").strip()
    target_amount = _parse_amount(args.get("target_amount"))
    target_date = args.get("target_date", "").strip()
    description = args.get("description", "").strip()

    # Validation
    if not name or len(name) == 0:
        return {
            "success": False,
            "message": "Nama target tabungan wajib diisi",
            "code": "MISSING_NAME",
            "ask_user": "Mohon sebutkan nama target tabungan (contoh: Liburan Bali, Dana Darurat, Laptop Baru)",
        }

    if not name or len(name) > 200:
        return {
            "success": False,
            "message": "Nama target terlalu panjang",
            "code": "NAME_TOO_LONG",
        }

    if target_amount is None or target_amount <= 0:
        return {
            "success": False,
            "message": "Target jumlah wajib diisi dan harus positif",
            "code": "MISSING_AMOUNT",
            "ask_user": "Mohon sebutkan target jumlah tabungan dalam rupiah",
        }

    # Parse target date if provided
    if target_date:
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            if dateparser:
                parsed_dt = dateparser.parse(target_date, locales=["id", "en"])
                if parsed_dt:
                    target_date = parsed_dt.date().isoformat()
                else:
                    # If dateparser fails, try to handle year-only format
                    if re.match(r'^\d{4}$', target_date):
                        target_date = f"{target_date}-12-31"
                    else:
                        return {
                            "success": False,
                            "message": "Format tanggal tidak valid. Gunakan YYYY-MM-DD atau format tanggal lengkap",
                            "code": "INVALID_DATE",
                            "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28) atau tanggal lengkap",
                        }

    try:
        logger.info(
            "create_savings_goal_started",
            user_id=user_id,
            name=name,
            target_amount=target_amount,
        )

        cur = db.cursor()
        cur.execute(
            """
            INSERT INTO savings_goals 
            (user_id, name, target_amount, description, target_date, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (user_id, name, target_amount, description, target_date),
        )
        goal_id = cur.fetchone()[0]
        db.commit()

        logger.info(
            "savings_goal_created",
            user_id=user_id,
            goal_id=goal_id,
            name=name,
        )

        return {
            "success": True,
            "message": f"✅ Target tabungan '{name}' berhasil dibuat (Target: Rp {target_amount:,.0f})",
            "goal_id": goal_id,
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
    """Execute delete transaction with safety checks"""

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
            "delete_transaction_started",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        cur = db.cursor()

        # Verify and delete
        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND user_id = %s RETURNING id",
            (transaction_id, user_id),
        )

        deleted = cur.fetchone()

        if not deleted:
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
    """Execute transfer between accounts with validation"""

    amount = _parse_amount(args.get("amount"))
    from_account = args.get("from_account", "").strip()
    to_account = args.get("to_account", "").strip()
    date = args.get("date")
    description = args.get("description", "Transfer").strip()

    # Validation
    if not amount or amount <= 0:
        return {
            "success": False,
            "message": "Jumlah transfer wajib diisi dan harus positif",
            "code": "INVALID_AMOUNT",
            "ask_user": "Mohon sebutkan jumlah yang akan ditransfer",
        }

    if not from_account:
        return {
            "success": False,
            "message": "Akun sumber wajib diisi",
            "code": "MISSING_FROM_ACCOUNT",
            "ask_user": "Mohon sebutkan akun sumber transfer",
        }

    if not to_account:
        return {
            "success": False,
            "message": "Akun tujuan wajib diisi",
            "code": "MISSING_TO_ACCOUNT",
            "ask_user": "Mohon sebutkan akun tujuan transfer",
        }

    if from_account == to_account:
        return {
            "success": False,
            "message": "Akun sumber dan tujuan tidak boleh sama",
            "code": "SAME_ACCOUNT",
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
                date or datetime.now().strftime("%Y-%m-%d"),
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
                date or datetime.now().strftime("%Y-%m-%d"),
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
