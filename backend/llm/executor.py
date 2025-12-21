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
from llm.input_interpreter import (
    interpret_input,
    get_interpreter,
    MatchConfidence,
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
                "message": "Apa jenis transaksi ini?",
                "code": "MISSING_TYPE",
                "ask_user": "Ini pemasukan atau pengeluaran?\n"
                "Contoh: 'Terima gaji 5 juta' atau 'Bayar cicilan 500k'",
                "requires_clarification": True,
            }

    # Parse amount
    amount = _parse_amount(args.get("amount"))
    if amount is None or amount <= 0:
        return {
            "success": False,
            "message": "Berapa jumlahnya?",
            "code": "MISSING_AMOUNT",
            "ask_user": "Jumlahnya berapa?\nContoh: '50 ribu', '500 ribu', '1 juta'",
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
            "message": "Kategori apa?",
            "code": "MISSING_CATEGORY",
            "ask_user": f"Kategorinya apa?\n"
            f"Pilihan: {', '.join(VALID_CATEGORIES_BY_TYPE.get(tx_type, []))}"
            + (f"\n🔍 Saran: {suggested}" if suggested else ""),
            "requires_clarification": True,
        }

    # Account is required - ask if not provided
    if not account:
        return {
            "success": False,
            "message": "Akun mana?",
            "code": "MISSING_ACCOUNT",
            "ask_user": "Akun mana yang dipakai?\n"
            "Misalnya: Cash, BCA, Gopay, Maybank, Seabank, OVO, dll",
            "requires_clarification": True,
        }

    # Interpret account with transparency - use input_interpreter
    interpreter = get_interpreter()
    account_interp = interpreter.interpret_account(account)

    if account_interp.confidence == MatchConfidence.NO_MATCH:
        # No match found
        return {
            "success": False,
            "message": account_interp.explanation,
            "code": "INVALID_ACCOUNT",
            "ask_user": account_interp.explanation,
            "requires_clarification": True,
        }

    # Extract normalized account
    account = account_interp.interpreted_value

    # If fuzzy matched, ask for confirmation with explanation
    if account_interp.needs_confirmation:
        confirmation_msg = interpreter.format_confirmation_message(account_interp)
        return {
            "success": False,
            "message": f"Jadi akun yang dipakai: {account}, benar?",
            "code": "CONFIRM_ACCOUNT",
            "ask_user": confirmation_msg,
            "requires_confirmation": True,
            "interpretation": account_interp.to_dict(),
        }

    # Date - ask user if not provided (don't default to today)
    if not date:
        return {
            "success": False,
            "message": "Kapan tanggalnya?",
            "code": "MISSING_DATE",
            "ask_user": "Tanggalnya kapan?\n"
            "Bisa 'hari ini', 'kemarin', 'besok', '20 desember', atau '2025-12-20'",
            "requires_clarification": True,
        }

    # Interpret date with transparency and confirmation
    date_interp = interpreter.interpret_date(date)

    if date_interp.confidence == MatchConfidence.NO_MATCH:
        return {
            "success": False,
            "message": date_interp.explanation,
            "code": "INVALID_DATE",
            "ask_user": date_interp.explanation,
            "requires_clarification": True,
        }

    normalized_date = date_interp.interpreted_value

    if date_interp.needs_confirmation:
        confirmation_msg = interpreter.format_confirmation_message(date_interp)
        return {
            "success": False,
            "message": f"Tanggalnya: {normalized_date}, benar?",
            "code": "CONFIRM_DATE",
            "ask_user": confirmation_msg,
            "requires_confirmation": True,
            "interpretation": date_interp.to_dict(),
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
            "ask_user": f"Coba lagi. {ve.message}",
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
            "message": f"✅ {validated['type'].capitalize()} Rp {validated['amount']:,.0f} dicatat ke {account}",
            "amount": validated["amount"],
            "category": validated["category"],
        }
    except Exception as e:
        logger.error("transaction_insert_error", user_id=user_id, error=str(e))
        result = {
            "success": False,
            "message": f"Oops, ada masalah saat menyimpan. Coba lagi ya.",
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
            "message": "Target tabungan apa?",
            "code": "MISSING_NAME",
            "ask_user": "Nama targetnya apa?\nMisalnya: Umroh, Liburan Bali, Dana Darurat, Laptop Baru",
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
            "message": "Target jumlahnya berapa?",
            "code": "MISSING_AMOUNT",
            "ask_user": "Targetnya berapa?\nMisalnya: '100 juta', '50000000', '1.5 miliar'",
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
            "message": "Kapan targetnya?",
            "code": "MISSING_TARGET_DATE",
            "ask_user": "Target tanggalnya kapan?\n"
            "Misalnya: '2025-12-31', '31 Desember 2025', atau '2030'",
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
            "message": f"✨ Target tabungan '{name}' berhasil dibuat! Target Rp {target_amount:,.0f} sampai {date_display}",
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
            "message": f"Oops, ada masalah saat membuat target. Coba lagi ya.",
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
            "message": "Transaksi ID berapa?",
            "code": "MISSING_ID",
            "ask_user": "Transaksi mana yang ingin dihapus? (berikan ID transaksinya)",
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
                "message": "Transaksi tidak ketemu. Cek ID lagi?",
                "code": "TRANSACTION_NOT_FOUND",
            }

        # Require confirmation for large amounts
        if tx_data["amount"] > 5_000_000:
            return {
                "success": False,
                "message": "Ini jumlah besar - yakin mau dihapus?",
                "code": "CONFIRM_DELETE",
                "ask_user": f"Yakin ingin hapus transaksi ini?\n\n"
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
                "message": "Oops, gagal menghapus. Coba lagi ya?",
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
            "message": f"✅ Transaksi #{transaction_id} terhapus",
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
            "message": f"Waduh, ada masalah. Coba lagi nanti ya.",
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
