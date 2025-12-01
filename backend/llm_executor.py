"""LLM action executor - handles all LLM-initiated financial operations

Adds meta logging for each tool invocation so changes appear in long-term memory
and feed summary generation & semantic search.
"""

from datetime import datetime, timedelta, timezone
import re

try:
    import dateparser  # type: ignore
except Exception:  # pragma: no cover
    dateparser = None
from database import get_db
from helpers import execute_transaction_from_llm


def execute_action(user_id, action_name, args):
    """Execute LLM action and return result dict with success status.

    Returns dict with keys: success (bool), message (str).
    Caller should handle logging and summary updates after successful execution.
    """
    db = get_db()
    today = datetime.now(timezone(timedelta(hours=7))).date()

    try:
        # ADD TRANSACTION (dengan alias untuk kompatibilitas Gemini)
        if action_name in [
            "add_transaction",
            "record_expense",
            "record_income",
            "add_expense",
            "add_income",
        ]:
            print(f"\n{'=' * 60}")
            print(f"[DEBUG] {action_name} DIPANGGIL dari LLM")
            print(f"[DEBUG] User ID: {user_id}")
            print(f"[DEBUG] Raw Arguments: {args}")

            # Deteksi tipe transaksi dari action name atau args
            tx_type = args.get("type")
            if not tx_type:
                # Auto-detect dari action name
                if "expense" in action_name or action_name == "record_expense":
                    tx_type = "expense"
                elif "income" in action_name or action_name == "record_income":
                    tx_type = "income"
                else:
                    tx_type = "expense"  # default

            print(f"[DEBUG] Detected transaction type: {tx_type}")

            tx_args = {
                "type": tx_type,
                "amount": args.get("amount"),
                "category": args.get("category"),
                "description": args.get("description", ""),
                "date": args.get("date", today.isoformat()),
                "account": args.get("account", "Cash"),
            }
            print(f"[DEBUG] Processed Transaction Args: {tx_args}")
            print("[DEBUG] Memanggil execute_transaction_from_llm...")
            print(f"{'=' * 60}\n")

            res = execute_transaction_from_llm(user_id, tx_args)

            print(f"\n{'=' * 60}")
            print(f"[DEBUG] Hasil dari execute_transaction_from_llm: {res}")
            print(f"{'=' * 60}\n")
            return res

        # CREATE SAVINGS GOAL
        elif action_name == "create_savings_goal":
            name = args.get("name")
            target_amount = args.get("target_amount")
            target_date = (args.get("target_date") or "").strip()

            # Validasi name
            if not name or not name.strip():
                return {
                    "success": False,
                    "message": "need_name",
                    "ask_user": "Mohon sebutkan nama target tabungan (contoh: Liburan Bali, Dana Darurat, Laptop Baru, dll.).",
                }

            # Validasi target_amount
            if not target_amount or float(target_amount) <= 0:
                return {
                    "success": False,
                    "message": "need_amount",
                    "ask_user": "Mohon sebutkan target jumlah tabungan dalam rupiah.",
                }

            # Normalize date if provided
            if target_date:
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", target_date):
                    parsed = None
                    if dateparser is not None:
                        parsed_dt = dateparser.parse(target_date, locales=["id", "en"])  # type: ignore
                        if parsed_dt:
                            parsed = parsed_dt.date().isoformat()
                    if not parsed:
                        return {
                            "success": False,
                            "message": "need_date",
                            "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                        }
                    target_date = parsed

            db.execute(
                "INSERT INTO savings_goals (user_id, name, target_amount, current_amount, description, target_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    name,
                    float(target_amount),
                    0,
                    args.get("description", ""),
                    target_date or None,
                ),
            )
            db.commit()
            res = {
                "success": True,
                "message": f"Target tabungan '{name}' berhasil dibuat",
            }
            return res

        # UPDATE TRANSACTION
        elif action_name == "update_transaction":
            print(f"\n{'=' * 60}")
            print("[DEBUG] update_transaction DIPANGGIL")
            print(f"[DEBUG] User ID: {user_id}")
            print(f"[DEBUG] Arguments diterima: {args}")

            tx_id = args.get("id")
            print(f"[DEBUG] Transaction ID: {tx_id}")

            if not tx_id:
                print("[DEBUG] ERROR: ID transaksi tidak ada")
                print(f"{'=' * 60}\n")
                return {
                    "success": False,
                    "message": "need_id",
                    "ask_user": "Mohon sebutkan ID transaksi yang akan diupdate.",
                }

            cur = db.execute(
                "SELECT id FROM transactions WHERE id = ? AND user_id = ?",
                (tx_id, user_id),
            ).fetchone()

            if not cur:
                print("[DEBUG] ERROR: Transaksi tidak ditemukan di database")
                print(f"{'=' * 60}\n")
                return {"success": False, "message": "Transaksi tidak ditemukan"}

            print("[DEBUG] Transaksi ditemukan di database")

            fields = []
            vals = []
            # Basic validations on optional fields
            if "amount" in args:
                try:
                    if float(args["amount"]) <= 0:
                        return {
                            "success": False,
                            "message": "need_amount",
                            "ask_user": "Jumlah harus lebih dari 0. Mohon berikan jumlah yang valid.",
                        }
                except Exception:
                    return {
                        "success": False,
                        "message": "need_amount",
                        "ask_user": "Jumlah tidak valid. Mohon berikan angka rupiah yang valid.",
                    }
            if "type" in args and args["type"] not in ["income", "expense", "transfer"]:
                return {
                    "success": False,
                    "message": "need_type",
                    "ask_user": "Tipe tidak valid. Apakah ini income, expense, atau transfer?",
                }
            for f in ["date", "type", "category", "description", "amount", "account"]:
                if f in args and args[f] not in [None, ""]:
                    val = args[f]
                    if f == "date":
                        s = str(val).strip()
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                            parsed = None
                            if dateparser is not None:
                                parsed_dt = dateparser.parse(s, locales=["id", "en"])  # type: ignore
                                if parsed_dt:
                                    parsed = parsed_dt.date().isoformat()
                            if not parsed:
                                return {
                                    "success": False,
                                    "message": "need_date",
                                    "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                                }
                            val = parsed
                    fields.append(f"{f} = ?")
                    vals.append(val)
                    print(f"[DEBUG] Field '{f}' akan diupdate: {val}")

            if not fields:
                print("[DEBUG] ERROR: Tidak ada field untuk diupdate")
                print(f"{'=' * 60}\n")
                return {
                    "success": False,
                    "message": "no_updates",
                    "ask_user": "Tidak ada field yang bisa diupdate. Mohon sebutkan field yang ingin diubah (date, type, category, description, amount, account).",
                }

            vals.extend([tx_id, user_id])
            sql_query = f"UPDATE transactions SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
            print(f"[DEBUG] SQL Query: {sql_query}")
            print(f"[DEBUG] SQL Values: {tuple(vals)}")

            db.execute(sql_query, tuple(vals))
            db.commit()

            print("[DEBUG] ✅ Transaksi berhasil diupdate!")
            print(f"[DEBUG] Total fields diupdate: {len(fields)}")
            print(f"{'=' * 60}\n")
            return {"success": True, "message": "Transaksi berhasil diupdate"}

        # DELETE TRANSACTION
        elif action_name == "delete_transaction":
            tx_id = args.get("id")
            if not tx_id:
                return {
                    "success": False,
                    "message": "need_id",
                    "ask_user": "Mohon sebutkan ID transaksi yang akan dihapus.",
                }

            db.execute(
                "DELETE FROM transactions WHERE id = ? AND user_id = ?",
                (tx_id, user_id),
            )
            db.commit()
            return {"success": True, "message": "Transaksi berhasil dihapus"}

        # TRANSFER FUNDS
        elif action_name == "transfer_funds":
            amount = args.get("amount")
            fa = args.get("from_account")
            ta = args.get("to_account")

            # Validasi amount
            if not amount:
                return {
                    "success": False,
                    "message": "need_amount",
                    "ask_user": "Mohon sebutkan jumlah yang ingin ditransfer.",
                }

            # Validasi from_account
            if not fa:
                return {
                    "success": False,
                    "message": "need_account",
                    "ask_user": "Mohon sebutkan akun asal transfer (contoh: BCA, Cash, Gopay, dll.).",
                }

            # Validasi to_account
            if not ta:
                return {
                    "success": False,
                    "message": "need_account",
                    "ask_user": "Mohon sebutkan akun tujuan transfer (contoh: BCA, Cash, Gopay, dll.).",
                }

            if fa == ta:
                return {
                    "success": False,
                    "message": "need_account",
                    "ask_user": "Akun asal dan tujuan tidak boleh sama. Mohon pilih akun yang berbeda.",
                }

            # Normalisasi account names (case-insensitive)
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
                "blu": "Blu Account (Saving)",
                "blu account": "Blu Account (Saving)",
                "blu account (saving)": "Blu Account (Saving)",
            }
            fa_normalized = account_mapping.get(str(fa).lower(), fa)
            ta_normalized = account_mapping.get(str(ta).lower(), ta)

            # Normalize date if provided
            if args.get("date"):
                s = str(args.get("date")).strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                    parsed = None
                    if dateparser is not None:
                        parsed_dt = dateparser.parse(s, locales=["id", "en"])  # type: ignore
                        if parsed_dt:
                            parsed = parsed_dt.date().isoformat()
                    if not parsed:
                        return {
                            "success": False,
                            "message": "need_date",
                            "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                        }
                    date_str = parsed
                else:
                    date_str = s
            else:
                date_str = today.isoformat()
            desc = (
                args.get("description")
                or f"Transfer {fa_normalized} -> {ta_normalized}"
            )

            print(f"\n{'=' * 60}")
            print("[DEBUG] TRANSFER FUNDS")
            print(f"[DEBUG] Amount: {amount}")
            print(f"[DEBUG] From (raw): {fa} → (normalized): {fa_normalized}")
            print(f"[DEBUG] To (raw): {ta} → (normalized): {ta_normalized}")
            print(f"{'=' * 60}\n")

            try:
                db.execute("BEGIN")
                db.execute(
                    "INSERT INTO transactions (user_id, date, type, category, description, amount, account) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        date_str,
                        "transfer",
                        f"Ke {ta_normalized}",
                        desc,
                        -abs(float(amount)),
                        fa_normalized,
                    ),
                )
                print(f"[DEBUG] ✅ Debit dari {fa_normalized}: -{amount}")

                db.execute(
                    "INSERT INTO transactions (user_id, date, type, category, description, amount, account) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        date_str,
                        "transfer",
                        f"Dari {fa_normalized}",
                        desc,
                        abs(float(amount)),
                        ta_normalized,
                    ),
                )
                print(f"[DEBUG] ✅ Kredit ke {ta_normalized}: +{amount}")
                db.commit()
                print("[DEBUG] ✅ Transfer berhasil di-commit ke database")
                print(f"{'=' * 60}\n")
                return {
                    "success": True,
                    "message": f"Transfer Rp {amount:,.0f} dari {fa_normalized} ke {ta_normalized} berhasil".replace(
                        ",", "."
                    ),
                }
            except Exception as te:
                db.rollback()
                return {"success": False, "message": f"Transfer gagal: {te}"}

        # UPDATE SAVINGS GOAL
        elif action_name == "update_savings_goal":
            gid = args.get("id") or args.get("goal_id")
            if not gid:
                # Try to find by name if provided
                goal_name = args.get("name") or args.get("goal_name")
                if goal_name:
                    cur = db.execute(
                        "SELECT id, name FROM savings_goals WHERE user_id = ? AND LOWER(name) LIKE ?",
                        (user_id, f"%{goal_name.lower()}%"),
                    ).fetchone()
                    if cur:
                        gid = cur["id"]
                    else:
                        goals = db.execute(
                            "SELECT id, name FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC",
                            (user_id,),
                        ).fetchall()
                        if goals:
                            goals_list = ", ".join([f"'{g['name']}'" for g in goals])
                            return {
                                "success": False,
                                "message": "need_goal",
                                "ask_user": f"Target tabungan '{goal_name}' tidak ditemukan. Mungkin maksudnya salah satu dari: {goals_list}?",
                            }
                        return {
                            "success": False,
                            "message": "need_goal",
                            "ask_user": "Kamu belum punya target tabungan. Mau buat yang baru dulu?",
                        }

                # No ID and no name
                goals = db.execute(
                    "SELECT id, name FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
                if not goals:
                    return {
                        "success": False,
                        "message": "need_goal",
                        "ask_user": "Kamu belum punya target tabungan. Mau buat yang baru dulu?",
                    }
                goals_list = ", ".join([f"'{g['name']}'" for g in goals])
                return {
                    "success": False,
                    "message": "need_goal",
                    "ask_user": f"Target tabungan mana yang mau diubah? Pilih dari: {goals_list}",
                }

            cur = db.execute(
                "SELECT id, name FROM savings_goals WHERE id = ? AND user_id = ?",
                (gid, user_id),
            ).fetchone()
            if not cur:
                return {
                    "success": False,
                    "message": "need_goal",
                    "ask_user": "Target tabungan tidak ditemukan. Coba cek lagi nama atau ID-nya ya.",
                }

            fields = []
            vals = []

            # Handle deadline/target_date with flexible keys
            deadline_keys = ["target_date", "deadline", "due_date", "date"]
            deadline_value = None
            for key in deadline_keys:
                if key in args and args[key]:
                    deadline_value = args[key]
                    break

            # Validate and normalize specific fields
            new_name = args.get("new_name") or (
                args.get("name") if args.get("name") != cur["name"] else None
            )
            if new_name and new_name.strip():
                fields.append("name = ?")
                vals.append(new_name)

            if "target_amount" in args and args["target_amount"]:
                try:
                    ta = float(args["target_amount"])
                    if ta <= 0:
                        return {
                            "success": False,
                            "message": "need_amount",
                            "ask_user": "Jumlah targetnya harus lebih dari 0 ya. Mau berapa?",
                        }
                    fields.append("target_amount = ?")
                    vals.append(ta)
                except Exception:
                    return {
                        "success": False,
                        "message": "need_amount",
                        "ask_user": "Jumlahnya kurang jelas nih. Targetnya mau berapa?",
                    }

            if "description" in args:
                fields.append("description = ?")
                vals.append(args.get("description") or "")

            if deadline_value:
                td = str(deadline_value).strip()
                if td and not re.match(r"^\d{4}-\d{2}-\d{2}$", td):
                    # Try to parse natural-language date
                    parsed = None
                    if dateparser is not None:
                        parsed_dt = dateparser.parse(td, locales=["id", "en"])  # type: ignore
                        if parsed_dt:
                            parsed = parsed_dt.date().isoformat()
                    if not parsed:
                        return {
                            "success": False,
                            "message": "need_date",
                            "ask_user": f"Tanggal '{td}' kurang jelas. Bisa pakai format seperti 'akhir Februari 2026' atau '2026-02-28'?",
                        }
                    td = parsed
                fields.append("target_date = ?")
                vals.append(td or None)

            if not fields:
                return {
                    "success": False,
                    "message": "no_updates",
                    "ask_user": f"Apa yang mau diubah dari tabungan '{cur['name']}'? Bisa ganti nama, target jumlah, deadline, atau deskripsi.",
                }

            vals.extend([gid, user_id])
            db.execute(
                f"UPDATE savings_goals SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                tuple(vals),
            )
            db.commit()
            return {
                "success": True,
                "message": f"Oke, target tabungan '{cur['name']}' sudah diupdate!",
            }

        # TRANSFER TO SAVINGS
        elif action_name == "transfer_to_savings":
            amount = args.get("amount")
            fa = args.get("from_account")
            gid = args.get("goal_id")

            # Validasi amount
            if not amount:
                return {
                    "success": False,
                    "message": "need_amount",
                    "ask_user": "Mohon sebutkan jumlah yang ingin ditabung.",
                }

            # Validasi from_account
            if not fa:
                return {
                    "success": False,
                    "message": "need_account",
                    "ask_user": "Mohon sebutkan akun sumber dana (contoh: BCA, Cash, Gopay, dll.).",
                }

            # Validasi goal_id
            if not gid:
                # Ambil list savings goals user
                goals = db.execute(
                    "SELECT id, name FROM savings_goals WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()

                if not goals:
                    return {
                        "success": False,
                        "message": "Tidak ada target tabungan. Buat dulu target tabungan sebelum mentransfer.",
                    }

                goals_list = ", ".join([f"{g['name']} (ID: {g['id']})" for g in goals])
                return {
                    "success": False,
                    "message": "need_goal",
                    "ask_user": f"Mohon pilih target tabungan: {goals_list}",
                }

            goal = db.execute(
                "SELECT id, name, current_amount FROM savings_goals WHERE id = ? AND user_id = ?",
                (gid, user_id),
            ).fetchone()

            print(f"[DEBUG] Goal lookup - ID: {gid}, User: {user_id}")
            print(f"[DEBUG] Goal found: {goal}")

            if not goal:
                return {
                    "success": False,
                    "message": "need_goal",
                    "ask_user": "Target tabungan tidak ditemukan. Mohon pilih target tabungan yang valid.",
                }

            # Normalisasi account name (case-insensitive)
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
                "blu": "Blu Account (Saving)",
                "blu account": "Blu Account (Saving)",
                "blu account (saving)": "Blu Account (Saving)",
            }
            fa_normalized = account_mapping.get(str(fa).lower(), fa)

            # Normalize date if provided
            if args.get("date"):
                s = str(args.get("date")).strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                    parsed = None
                    if dateparser is not None:
                        parsed_dt = dateparser.parse(s, locales=["id", "en"])  # type: ignore
                        if parsed_dt:
                            parsed = parsed_dt.date().isoformat()
                    if not parsed:
                        return {
                            "success": False,
                            "message": "need_date",
                            "ask_user": "Mohon berikan tanggal dalam format YYYY-MM-DD (contoh: 2026-02-28).",
                        }
                    date_str = parsed
                else:
                    date_str = s
            else:
                date_str = today.isoformat()
            desc = args.get("description") or f"Menabung: {goal['name']}"

            print(f"\n{'=' * 60}")
            print("[DEBUG] TRANSFER TO SAVINGS")
            print(f"[DEBUG] Amount: {amount}")
            print(f"[DEBUG] From Account (raw): {fa} → (normalized): {fa_normalized}")
            print(f"[DEBUG] Goal: {goal['name']} (ID: {gid})")
            print(f"{'=' * 60}\n")

            try:
                db.execute("BEGIN")
                db.execute(
                    "INSERT INTO transactions (user_id, date, type, category, description, amount, account) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        date_str,
                        "expense",
                        "Tabungan",
                        desc,
                        float(amount),
                        fa_normalized,
                    ),
                )
                print(f"[DEBUG] ✅ Transaksi expense dicatat dari {fa_normalized}")

                old_current = float(goal["current_amount"])
                new_amt = old_current + float(amount)
                print(
                    f"[DEBUG] Calculating: {old_current} + {float(amount)} = {new_amt}"
                )

                db.execute(
                    "UPDATE savings_goals SET current_amount = ? WHERE id = ?",
                    (new_amt, gid),
                )
                print(
                    f"[DEBUG] ✅ UPDATE query executed: SET current_amount = {new_amt} WHERE id = {gid}"
                )

                # Verify update
                verify = db.execute(
                    "SELECT current_amount FROM savings_goals WHERE id = ? AND user_id = ?",
                    (gid, user_id),
                ).fetchone()
                print(
                    f"[DEBUG] Verified current_amount after update: {verify['current_amount'] if verify else 'NOT FOUND'}"
                )
                print(
                    f"[DEBUG] ✅ Savings goal updated: {goal['current_amount']} → {new_amt}"
                )

                db.commit()
                print("[DEBUG] ✅ Transfer to savings berhasil di-commit")
                print(f"{'=' * 60}\n")

                return {
                    "success": True,
                    "message": f"Rp {amount:,.0f} ditransfer dari {fa_normalized} ke tabungan '{goal['name']}'".replace(
                        ",", "."
                    ),
                }
            except Exception as se:
                db.rollback()
                return {"success": False, "message": f"Transfer gagal: {se}"}

        # UNKNOWN ACTION
        else:
            return {"success": False, "message": f"Aksi '{action_name}' tidak dikenal"}

    except Exception as err:
        return {"success": False, "message": f"Eksekusi gagal: {err}"}
