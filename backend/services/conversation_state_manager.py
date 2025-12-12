"""Conversation State Manager - Manages multi-turn conversation flows"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from database import get_db
from core import get_logger

logger = get_logger(__name__)

# State machine definitions per intent
STATE_MACHINES = {
    "add_transaction": {
        "initial_state": "AWAITING_AMOUNT",
        "states": [
            "AWAITING_AMOUNT",
            "AWAITING_CATEGORY",
            "AWAITING_ACCOUNT",
            "CONFIRMING",
            "READY_TO_EXECUTE",
        ],
        "required_fields": ["amount", "type", "category", "account"],
    },
    "edit_transaction": {
        "initial_state": "AWAITING_AMOUNT",
        "states": [
            "AWAITING_FIELD",
            "AWAITING_NEW_VALUE",
            "CONFIRMING",
            "READY_TO_EXECUTE",
        ],
        "required_fields": ["field", "new_value"],
    },
    "delete_transaction": {
        "initial_state": "CONFIRMING",
        "states": ["CONFIRMING", "AWAITING_PASSWORD", "READY_TO_EXECUTE"],
        "required_fields": ["password"],
    },
    "transfer": {
        "initial_state": "AWAITING_FROM_ACCOUNT",
        "states": [
            "AWAITING_FROM_ACCOUNT",
            "AWAITING_TO_ACCOUNT",
            "AWAITING_AMOUNT",
            "CONFIRMING",
            "READY_TO_EXECUTE",
        ],
        "required_fields": ["from_account", "to_account", "amount"],
    },
    "create_goal": {
        "initial_state": "AWAITING_GOAL_NAME",
        "states": [
            "AWAITING_GOAL_NAME",
            "AWAITING_TARGET_AMOUNT",
            "AWAITING_DEADLINE",
            "CONFIRMING",
            "READY_TO_EXECUTE",
        ],
        "required_fields": ["name", "target_amount", "deadline"],
    },
}

# State transition logic: what question to ask at each state
STATE_PROMPTS = {
    "add_transaction": {
        "AWAITING_AMOUNT": "Berapa jumlahnya? (misal: 50 ribu, 100k, 5 juta)",
        "AWAITING_CATEGORY": "Kategori apa? (misal: Makanan, Transport, Entertainment, dsb)",
        "AWAITING_ACCOUNT": "Dari akun mana? (misal: Cash, BCA, OVO, Gopay)",
        "CONFIRMING": "Catat {type}: {amount} untuk {category} dari {account}? (Catat/Batal)",
    },
    "transfer": {
        "AWAITING_FROM_ACCOUNT": "Transfer dari akun mana? (misal: Cash, BCA)",
        "AWAITING_TO_ACCOUNT": "Transfer ke akun mana? (misal: Savings, OVO)",
        "AWAITING_AMOUNT": "Berapa jumlahnya yang di-transfer?",
        "CONFIRMING": "Transfer {amount} dari {from_account} ke {to_account}? (Konfirmasi/Batal)",
    },
    "delete_transaction": {
        "CONFIRMING": "Hapus transaksi ini? Aksi ini tidak dapat dibatalkan. (Hapus/Batal)",
        "AWAITING_PASSWORD": "Masukkan password untuk konfirmasi penghapusan:",
    },
    "create_goal": {
        "AWAITING_GOAL_NAME": "Target tabungan untuk apa? (misal: Liburan, Laptop, Rumah)",
        "AWAITING_TARGET_AMOUNT": "Target berapa jumlahnya?",
        "AWAITING_DEADLINE": "Target kapan? (misal: 6 bulan, akhir tahun, 2026-12-31)",
        "CONFIRMING": "Buat target tabungan: {name} target {target_amount} hingga {deadline}? (Buat/Batal)",
    },
}


class ConversationStateManager:
    """Manage multi-turn conversation state per session"""

    @staticmethod
    def init_state(user_id: int, session_id: int, intent: str) -> Tuple[bool, Dict]:
        """Initialize new conversation state for an intent"""
        if intent not in STATE_MACHINES:
            return False, {"error": f"Unknown intent: {intent}"}

        sm = STATE_MACHINES[intent]
        initial_state = sm["initial_state"]

        try:
            db = get_db()

            # Clear any existing state for this session
            db.execute(
                "DELETE FROM conversation_state WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP",
                (session_id,),
            )

            # Insert new state
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            db.execute(
                """
                INSERT INTO conversation_state 
                (user_id, session_id, intent, state, partial_data, expires_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    user_id,
                    session_id,
                    intent,
                    initial_state,
                    json.dumps({}),
                    expires_at,
                ),
            )
            db.commit()

            prompt = STATE_PROMPTS.get(intent, {}).get(
                initial_state, "Lanjutkan informasi yang dibutuhkan:"
            )

            logger.info(
                "conversation_state_init",
                user_id=user_id,
                session_id=session_id,
                intent=intent,
                state=initial_state,
            )

            return True, {"intent": intent, "state": initial_state, "prompt": prompt}

        except Exception as e:
            logger.error("conversation_state_init_error", error=str(e))
            return False, {"error": str(e)}

    @staticmethod
    def get_state(session_id: int) -> Optional[Dict]:
        """Retrieve current conversation state"""
        try:
            db = get_db()

            # Clean expired states
            db.execute(
                "DELETE FROM conversation_state WHERE expires_at < CURRENT_TIMESTAMP"
            )
            db.commit()

            cur = db.execute(
                """
                SELECT id, user_id, intent, state, partial_data, expires_at
                FROM conversation_state
                WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP
                """,
                (session_id,),
            )
            row = cur.fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "intent": row["intent"],
                "state": row["state"],
                "partial_data": json.loads(row["partial_data"]),
                "expires_at": row["expires_at"],
            }
        except Exception as e:
            logger.error("get_state_error", error=str(e))
            return None

    @staticmethod
    def get_session_state(session_id: int) -> Dict:
        """Wrapper to get session state with success indicator"""
        state = ConversationStateManager.get_state(session_id)
        if state:
            return {
                "success": True,
                "state": state,
            }
        return {
            "success": False,
            "state": None,
        }

    @staticmethod
    def update_field(
        session_id: int, field_name: str, field_value: any
    ) -> Tuple[bool, Dict]:
        """Update a field and advance state"""
        try:
            state = ConversationStateManager.get_state(session_id)
            if not state:
                return False, {"error": "No active conversation state"}

            intent = state["intent"]
            current_state = state["state"]
            partial_data = state["partial_data"]

            # Update the field
            partial_data[field_name] = field_value

            # Determine next state
            sm = STATE_MACHINES[intent]
            current_idx = sm["states"].index(current_state)

            # If all required fields collected, go to CONFIRMING
            if all(field in partial_data for field in sm["required_fields"]):
                next_state = "CONFIRMING"
            # Otherwise, advance to next state
            elif current_idx + 1 < len(sm["states"]):
                next_state = sm["states"][current_idx + 1]
            else:
                next_state = "CONFIRMING"

            # Update in DB
            db = get_db()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            db.execute(
                """
                UPDATE conversation_state 
                SET state = ?, partial_data = ?, expires_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (next_state, json.dumps(partial_data), expires_at, state["id"]),
            )
            db.commit()

            # Get next prompt
            prompt = STATE_PROMPTS.get(intent, {}).get(
                next_state, "Lanjutkan informasi berikutnya:"
            )

            # Format prompt with current data
            try:
                prompt = prompt.format(**partial_data)
            except KeyError:
                pass  # Template has missing keys, show as-is

            logger.info(
                "conversation_state_update",
                session_id=session_id,
                intent=intent,
                old_state=current_state,
                new_state=next_state,
                field=field_name,
            )

            return True, {
                "state": next_state,
                "partial_data": partial_data,
                "prompt": prompt,
                "ready_to_execute": next_state == "READY_TO_EXECUTE",
            }

        except Exception as e:
            logger.error("update_field_error", error=str(e))
            return False, {"error": str(e)}

    @staticmethod
    def confirm(session_id: int, confirm: bool = True) -> Tuple[bool, Dict]:
        """User confirms or cancels the action"""
        try:
            state = ConversationStateManager.get_state(session_id)
            if not state:
                return False, {"error": "No active conversation state"}

            if not confirm:
                # Cancel: clean up state
                db = get_db()
                db.execute(
                    "DELETE FROM conversation_state WHERE id = ?", (state["id"],)
                )
                db.commit()
                logger.info("conversation_state_cancelled", session_id=session_id)
                return True, {"cancelled": True, "message": "Aksi dibatalkan"}

            # Confirm: set to READY_TO_EXECUTE
            if state["state"] != "CONFIRMING":
                return False, {"error": "Not in CONFIRMING state"}

            db = get_db()
            db.execute(
                """
                UPDATE conversation_state 
                SET state = 'READY_TO_EXECUTE', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (state["id"],),
            )
            db.commit()

            logger.info("conversation_state_confirmed", session_id=session_id)

            return True, {
                "ready_to_execute": True,
                "intent": state["intent"],
                "partial_data": state["partial_data"],
            }

        except Exception as e:
            logger.error("confirm_error", error=str(e))
            return False, {"error": str(e)}

    @staticmethod
    def clear_state(session_id: int) -> bool:
        """Clear state after execution"""
        try:
            db = get_db()
            db.execute(
                "DELETE FROM conversation_state WHERE session_id = ?", (session_id,)
            )
            db.commit()
            logger.info("conversation_state_cleared", session_id=session_id)
            return True
        except Exception as e:
            logger.error("clear_state_error", error=str(e))
            return False

    @staticmethod
    def get_next_question(session_id: int) -> Optional[str]:
        """Get the next question to ask user"""
        state = ConversationStateManager.get_state(session_id)
        if not state:
            return None

        intent = state["intent"]
        current_state = state["state"]

        prompt = STATE_PROMPTS.get(intent, {}).get(
            current_state, "Lanjutkan informasi berikutnya:"
        )

        # Format prompt with current data
        try:
            prompt = prompt.format(**state["partial_data"])
        except KeyError:
            pass

        return prompt
