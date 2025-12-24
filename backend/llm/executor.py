"""LLM action executor - handles all LLM-initiated financial operations with proper error handling

Uses TransactionService for safe operations with isolation and validation.
"""

from datetime import datetime, timedelta, timezone
import re
from typing import Dict, Any, Optional
from core import get_logger, TransactionValidator, ValidationError
from database import get_db
from financial_context import invalidate_financial_cache
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
from llm.interpreter_config import (
    get_error_message,
    get_explanation,
    get_confirmation_message,
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
    user_id: int, action_name: str, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """
    Execute LLM action with proper error handling and validation.

    Args:
        user_id: User ID
        action_name: Action name (add_transaction, create_savings_goal, etc)
        args: Action arguments
        lang: Language for response messages (id/en), default='id'

    Returns:
        Dict with success status and details
    """
    # Ensure lang is valid
    lang = lang if lang in ["id", "en"] else "id"

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
            return _execute_add_transaction(user_id, action_name, args, lang)

        # CREATE SAVINGS GOAL
        elif action_name == "create_savings_goal":
            return _execute_create_savings_goal(user_id, args, lang)

        # UPDATE TRANSACTION
        elif action_name == "update_transaction":
            return _execute_update_transaction(user_id, args, lang)

        # DELETE TRANSACTION
        elif action_name == "delete_transaction":
            return _execute_delete_transaction(user_id, args, lang)

        # TRANSFER FUNDS
        elif action_name == "transfer_funds":
            return _execute_transfer_funds(user_id, args, lang)

        else:
            logger.warning("unknown_action", action=action_name, user_id=user_id)
            unknown_msg = (
                f"Aksi '{action_name}' tidak dikenal"
                if lang == "id"
                else f"Action '{action_name}' not recognized"
            )
            return {
                "success": False,
                "message": unknown_msg,
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
    user_id: int, action_name: str, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """Execute add transaction with validation and isolation"""
    lang = lang if lang in ["id", "en"] else "id"

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
            type_message = (
                "Apa jenis transaksi ini?"
                if lang == "id"
                else "What type of transaction is this?"
            )
            type_ask = (
                "Ini pemasukan atau pengeluaran?\nContoh: 'Terima gaji 5 juta' atau 'Bayar cicilan 500k'"
                if lang == "id"
                else "Is this income or expense?\nExample: 'Receive salary 5 million' or 'Pay installment 500k'"
            )
            return {
                "success": False,
                "message": type_message,
                "code": "MISSING_TYPE",
                "ask_user": type_ask,
                "requires_clarification": True,
            }

    # Parse amount
    amount = _parse_amount(args.get("amount"))
    if amount is None or amount <= 0:
        amount_message = "Berapa jumlahnya?" if lang == "id" else "What's the amount?"
        amount_ask = (
            "Jumlahnya berapa?\nContoh: '50 ribu', '500 ribu', '1 juta'"
            if lang == "id"
            else "What's the amount?\nExample: '50k', '500k', '1 million'"
        )
        return {
            "success": False,
            "message": amount_message,
            "code": "MISSING_AMOUNT",
            "ask_user": amount_ask,
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
        category_message = "Kategori apa?" if lang == "id" else "What's the category?"
        category_ask = (
            f"Kategorinya apa?\nPilihan: {', '.join(VALID_CATEGORIES_BY_TYPE.get(tx_type, []))}"
            if lang == "id"
            else f"What's the category?\nOptions: {', '.join(VALID_CATEGORIES_BY_TYPE.get(tx_type, []))}"
        )
        if suggested:
            category_ask += (
                f"\n🔍 Saran: {suggested}"
                if lang == "id"
                else f"\n🔍 Suggestion: {suggested}"
            )
        return {
            "success": False,
            "message": category_message,
            "code": "MISSING_CATEGORY",
            "ask_user": category_ask,
            "requires_clarification": True,
        }

    # Account is required - ask if not provided
    if not account:
        account_message = "Akun mana?" if lang == "id" else "Which account?"
        account_ask = (
            "Akun mana yang dipakai?\nMisalnya: Cash, BCA, Gopay, Maybank, Seabank, OVO, dll"
            if lang == "id"
            else "Which account are you using?\nExample: Cash, BCA, Gopay, Maybank, Seabank, OVO, etc"
        )
        return {
            "success": False,
            "message": account_message,
            "code": "MISSING_ACCOUNT",
            "ask_user": account_ask,
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
        confirm_message = (
            f"Jadi akun yang dipakai: {account}, benar?"
            if lang == "id"
            else f"So the account used is: {account}, right?"
        )
        return {
            "success": False,
            "message": confirm_message,
            "code": "CONFIRM_ACCOUNT",
            "ask_user": confirmation_msg,
            "requires_confirmation": True,
            "interpretation": account_interp.to_dict(),
        }

    # Date - ask user if not provided (don't default to today)
    if not date:
        date_message = "Kapan tanggalnya?" if lang == "id" else "When is the date?"
        date_ask = (
            "Tanggalnya kapan?\nBisa 'hari ini', 'kemarin', 'besok', '20 desember', atau '2025-12-20'"
            if lang == "id"
            else "When is the date?\nCan be 'today', 'yesterday', 'tomorrow', 'Dec 20', or '2025-12-20'"
        )
        return {
            "success": False,
            "message": date_message,
            "code": "MISSING_DATE",
            "ask_user": date_ask,
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
        date_confirm_message = (
            f"Tanggalnya: {normalized_date}, benar?"
            if lang == "id"
            else f"The date is: {normalized_date}, right?"
        )
        return {
            "success": False,
            "message": date_confirm_message,
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
        error_prefix = "Coba lagi. " if lang == "id" else "Try again. "
        return {
            "success": False,
            "message": ve.message,
            "code": ve.code,
            "ask_user": f"{error_prefix}{ve.message}",
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
        invalidate_financial_cache()  # Clear cache after transaction added
        type_label = validated["type"].capitalize()
        if lang == "en":
            type_label = "Income" if validated["type"] == "income" else "Expense"
        success_message = (
            f"✅ {type_label} Rp {validated['amount']:,.0f} dicatat ke {account}"
            if lang == "id"
            else f"✅ {type_label} Rp {validated['amount']:,.0f} recorded to {account}"
        )
        result = {
            "success": True,
            "message": success_message,
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


def _execute_create_savings_goal(
    user_id: int, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """Execute create savings goal with validation - NO DEFAULTS"""

    db = get_db()
    name = args.get("name", "").strip()
    target_amount = _parse_amount(args.get("target_amount"))
    target_date = args.get("target_date", "").strip()
    description = args.get("description", "").strip()

    # Validation - name required
    if not name:
        name_msg = (
            "Target tabungan apa?" if lang == "id" else "What's your savings goal?"
        )
        name_ask = (
            "Nama targetnya apa?\nMisalnya: Umroh, Liburan Bali, Dana Darurat, Laptop Baru"
            if lang == "id"
            else "What's the goal name?\nExample: Umroh, Bali Vacation, Emergency Fund, New Laptop"
        )
        return {
            "success": False,
            "message": name_msg,
            "code": "MISSING_NAME",
            "ask_user": name_ask,
            "requires_clarification": True,
        }

    # Validate name length
    is_valid, name_error = validate_name(
        name, "Nama target tabungan", {"min_length": 1, "max_length": 100}
    )
    if not is_valid:
        name_error_msg = name_error if lang == "id" else "Invalid goal name"
        return {
            "success": False,
            "message": name_error_msg,
            "code": "INVALID_NAME",
            "ask_user": name_error_msg,
            "requires_clarification": True,
        }

    # Validate amount required
    if target_amount is None or target_amount <= 0:
        amount_msg = (
            "Target jumlahnya berapa?" if lang == "id" else "What's the target amount?"
        )
        amount_ask = (
            "Targetnya berapa?\nMisalnya: '100 juta', '50000000', '1.5 miliar'"
            if lang == "id"
            else "What's the target amount?\nExample: '100 million', '50000000', '1.5 billion'"
        )
        return {
            "success": False,
            "message": amount_msg,
            "code": "MISSING_AMOUNT",
            "ask_user": amount_ask,
            "requires_clarification": True,
        }

    # Validate amount not too large
    is_valid, amount_error = validate_amount(target_amount, "Target jumlah")
    if not is_valid:
        amount_error_msg = (
            amount_error if lang == "id" else "Target amount is too large"
        )
        return {
            "success": False,
            "message": amount_error_msg,
            "code": "INVALID_AMOUNT",
            "ask_user": amount_error_msg,
            "requires_clarification": True,
        }

    # Target date: ASK user if not provided (don't default to null)
    if not target_date:
        date_msg = "Kapan targetnya?" if lang == "id" else "When is the target date?"
        date_ask = (
            "Target tanggalnya kapan?\n"
            "Misalnya: '2025-12-31', '31 Desember 2025', atau '2030'"
            if lang == "id"
            else "When is the target date?\n"
            "Example: '2025-12-31', '31 December 2025', or '2030'"
        )
        return {
            "success": False,
            "message": date_msg,
            "code": "MISSING_TARGET_DATE",
            "ask_user": date_ask,
            "requires_clarification": True,
        }

    # Parse target date
    is_valid_date, normalized_date, date_error = validate_date(target_date)
    if not is_valid_date:
        date_error_msg = date_error if lang == "id" else "Invalid target date"
        return {
            "success": False,
            "message": date_error_msg,
            "code": "INVALID_DATE",
            "ask_user": date_error_msg,
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

        success_msg = (
            f"✨ Target tabungan '{name}' berhasil dibuat! Target Rp {target_amount:,.0f} sampai {date_display}"
            if lang == "id"
            else f"✨ Savings goal '{name}' created successfully! Target ${target_amount:,.0f} by {date_display}"
        )
        return {
            "success": True,
            "message": success_msg,
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


def _execute_update_transaction(
    user_id: int, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """Execute update transaction with validation"""

    transaction_id = args.get("id")

    if not transaction_id:
        id_msg = (
            "ID transaksi wajib diisi" if lang == "id" else "Transaction ID is required"
        )
        return {
            "success": False,
            "message": id_msg,
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
            not_found_msg = (
                "Transaksi tidak ditemukan atau bukan milik Anda"
                if lang == "id"
                else "Transaction not found or doesn't belong to you"
            )
            return {
                "success": False,
                "message": not_found_msg,
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
        invalidate_financial_cache()  # Clear cache after transaction updated

        logger.info(
            "transaction_updated",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        success_msg = (
            f"✅ Transaksi #{transaction_id} berhasil diperbarui"
            if lang == "id"
            else f"✅ Transaction #{transaction_id} updated successfully"
        )
        return {
            "success": True,
            "message": success_msg,
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
        error_msg = (
            f"Gagal memperbarui transaksi: {str(e)}"
            if lang == "id"
            else f"Failed to update transaction: {str(e)}"
        )
        return {
            "success": False,
            "message": error_msg,
            "code": "UPDATE_FAILED",
        }


def _execute_delete_transaction(
    user_id: int, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """Execute delete transaction with mandatory confirmation for safety"""

    transaction_id = args.get("id")
    confirm = args.get("confirm", False)  # Check if user confirmed

    if not transaction_id:
        id_msg = "Transaksi ID berapa?" if lang == "id" else "Which transaction ID?"
        id_ask = (
            "Transaksi mana yang ingin dihapus? (berikan ID transaksinya)"
            if lang == "id"
            else "Which transaction do you want to delete? (provide the transaction ID)"
        )
        return {
            "success": False,
            "message": id_msg,
            "code": "MISSING_ID",
            "ask_user": id_ask,
            "requires_clarification": True,
        }

    try:
        db = get_db()

        # If not confirmed yet, get transaction details and ask for confirmation
        if not confirm:
            logger.info(
                "delete_transaction_confirmation_requested",
                user_id=user_id,
                transaction_id=transaction_id,
            )

            cur = db.cursor()
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
                not_found_msg = (
                    "Transaksi tidak ketemu. Cek ID lagi?"
                    if lang == "id"
                    else "Transaction not found. Check the ID again?"
                )
                return {
                    "success": False,
                    "message": not_found_msg,
                    "code": "TRANSACTION_NOT_FOUND",
                }

            # ALWAYS require confirmation before deleting (irreversible operation)
            type_label = "Pemasukan" if tx_data["type"] == "income" else "Pengeluaran"
            if lang == "en":
                type_label = "Income" if tx_data["type"] == "income" else "Expense"

            confirm_ask = (
                f"⚠️  Yakin ingin menghapus transaksi ini? (Tidak bisa dikembalikan)\n\n"
                f"📅 Tanggal: {tx_data['date']}\n"
                f"🏷️  Tipe: {type_label}\n"
                f"💰 Jumlah: Rp {tx_data['amount']:,.0f}\n"
                f"📂 Kategori: {tx_data['category']}\n"
                f"📝 Deskripsi: {tx_data['description'] or '-'}\n"
                f"💳 Akun: {tx_data['account']}\n\n"
                f"Balas 'ya' atau 'hapus' untuk konfirmasi"
                if lang == "id"
                else f"⚠️  Are you sure you want to delete this transaction? (Cannot be undone)\n\n"
                f"📅 Date: {tx_data['date']}\n"
                f"🏷️  Type: {type_label}\n"
                f"💰 Amount: Rp {tx_data['amount']:,.0f}\n"
                f"📂 Category: {tx_data['category']}\n"
                f"📝 Description: {tx_data['description'] or '-'}\n"
                f"💳 Account: {tx_data['account']}\n\n"
                f"Reply 'yes' or 'delete' to confirm"
            )

            return {
                "success": False,
                "message": "Konfirmasi hapus transaksi"
                if lang == "id"
                else "Confirm delete transaction",
                "code": "CONFIRM_DELETE",
                "ask_user": confirm_ask,
                "requires_confirmation": True,
                "transaction_id": transaction_id,
                "transaction_preview": {
                    "date": tx_data["date"],
                    "type": tx_data["type"],
                    "category": tx_data["category"],
                    "amount": float(tx_data["amount"]),
                    "description": tx_data["description"],
                    "account": tx_data["account"],
                },
            }

        # Confirmation received - proceed with delete
        logger.info(
            "delete_transaction_started",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        cur = db.cursor()

        # Delete transaction
        cur.execute(
            "DELETE FROM transactions WHERE id = %s AND user_id = %s RETURNING id",
            (transaction_id, user_id),
        )

        deleted = cur.fetchone()
        if not deleted:
            error_msg = (
                "Oops, gagal menghapus. Coba lagi ya?"
                if lang == "id"
                else "Oops, failed to delete. Please try again?"
            )
            return {
                "success": False,
                "message": error_msg,
                "code": "DELETE_FAILED",
            }

        db.commit()
        invalidate_financial_cache()  # Clear cache after transaction deleted

        logger.info(
            "transaction_deleted",
            user_id=user_id,
            transaction_id=transaction_id,
        )

        success_msg = (
            f"✅ Transaksi #{transaction_id} terhapus"
            if lang == "id"
            else f"✅ Transaction #{transaction_id} deleted"
        )
        return {
            "success": True,
            "message": success_msg,
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
        error_msg = (
            "Waduh, ada masalah. Coba lagi nanti ya."
            if lang == "id"
            else "Something went wrong. Please try again later."
        )
        return {
            "success": False,
            "message": error_msg,
            "code": "DELETE_FAILED",
        }


def _execute_transfer_funds(
    user_id: int, args: Dict[str, Any], lang: str = "id"
) -> Dict[str, Any]:
    """Execute transfer between accounts with validation - NO DEFAULTS"""

    amount = _parse_amount(args.get("amount"))
    from_account = args.get("from_account", "").strip()
    to_account = args.get("to_account", "").strip()
    date = args.get("date")
    description = args.get("description", "").strip()

    # Validate amount
    if not amount or amount <= 0:
        amount_msg = (
            "Jumlah transfer harus positif"
            if lang == "id"
            else "Transfer amount must be positive"
        )
        amount_ask = (
            "Berapa jumlah yang akan ditransfer?\nContoh: '100 ribu', '1 juta', '500000'"
            if lang == "id"
            else "How much do you want to transfer?\nExample: '100k', '1 million', '500000'"
        )
        return {
            "success": False,
            "message": amount_msg,
            "code": "MISSING_AMOUNT",
            "ask_user": amount_ask,
            "requires_clarification": True,
        }

    # Validate amount not too large
    is_valid, amount_error = validate_amount(amount, "Jumlah transfer")
    if not is_valid:
        amount_error_msg = (
            amount_error if lang == "id" else "Transfer amount is too large"
        )
        return {
            "success": False,
            "message": amount_error_msg,
            "code": "INVALID_AMOUNT",
            "ask_user": amount_error_msg,
            "requires_clarification": True,
        }

    # From account is required
    if not from_account:
        from_msg = (
            "Akun sumber wajib diisi" if lang == "id" else "Source account is required"
        )
        from_ask = (
            "Dari akun mana?\nPilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya"
            if lang == "id"
            else "From which account?\nOptions: Cash, BCA, Gopay, Maybank, Seabank, and more"
        )
        return {
            "success": False,
            "message": from_msg,
            "code": "MISSING_FROM_ACCOUNT",
            "ask_user": from_ask,
            "requires_clarification": True,
        }

    # To account is required
    if not to_account:
        to_msg = (
            "Akun tujuan wajib diisi"
            if lang == "id"
            else "Destination account is required"
        )
        to_ask = (
            "Ke akun mana?\nPilihan: Cash, BCA, Gopay, Maybank, Seabank, dan lainnya"
            if lang == "id"
            else "To which account?\nOptions: Cash, BCA, Gopay, Maybank, Seabank, and more"
        )
        return {
            "success": False,
            "message": to_msg,
            "code": "MISSING_TO_ACCOUNT",
            "ask_user": to_ask,
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
        same_msg = (
            "Akun sumber dan tujuan harus berbeda"
            if lang == "id"
            else "Source and destination accounts must be different"
        )
        return {
            "success": False,
            "message": same_msg,
            "code": "SAME_ACCOUNT",
            "ask_user": f"Akun '{from_account}' tidak bisa transfer ke dirinya sendiri."
            if lang == "id"
            else f"Account '{from_account}' cannot transfer to itself.",
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
        balance_msg = "Saldo tidak cukup" if lang == "id" else "Insufficient balance"
        balance_ask = (
            f"Saldo {from_account}: Rp {cur_balance:,.0f}\n"
            f"Tidak cukup untuk transfer Rp {amount:,.0f}\n"
            f"Kurang: Rp {amount - cur_balance:,.0f}"
            if lang == "id"
            else f"Balance {from_account}: Rp {cur_balance:,.0f}\n"
            f"Not enough for transfer of Rp {amount:,.0f}\n"
            f"Shortfall: Rp {amount - cur_balance:,.0f}"
        )
        return {
            "success": False,
            "message": balance_msg,
            "code": "INSUFFICIENT_BALANCE",
            "ask_user": balance_ask,
            "requires_clarification": True,
            "available_balance": cur_balance,
            "required_amount": amount,
            "shortfall": amount - cur_balance,
        }

    # Date: ask if not provided
    if not date:
        date_msg = (
            "Tanggal transfer harus diisi"
            if lang == "id"
            else "Transfer date is required"
        )
        date_ask = (
            "Kapan transfernya?\nFormat: 'hari ini', 'kemarin', '20 desember', atau '2025-12-20'"
            if lang == "id"
            else "When is the transfer?\nFormat: 'today', 'yesterday', '20 December', or '2025-12-20'"
        )
        return {
            "success": False,
            "message": date_msg,
            "code": "MISSING_DATE",
            "ask_user": date_ask,
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
        invalidate_financial_cache()  # Clear cache after transfer completed

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
