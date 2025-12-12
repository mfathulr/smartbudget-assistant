"""
Interaction Data Handler
Untuk aksi pada data: catat, edit, hapus, transfer, dsb.
Dengan validasi ketat, audit, dan konfirmasi.
"""

from typing import Dict, Any


class InteractionDataHandler:
    """Handle data modification requests (record, edit, delete, transfer, goal)"""

    @staticmethod
    def handle(
        query: str,
        user_id: int,
        intent_type: str,
        db,
        language: str = "id",
    ) -> Dict[str, Any]:
        """
        Handle interaction data request.
        Returns validation result and routing info for LLM execution.

        Args:
            query: User query
            user_id: User ID
            intent_type: Type like 'record', 'edit', 'delete', 'transfer', 'goal'
            db: Database connection
            language: Response language

        Returns:
            Dict with validation status and required confirmations
        """

        if intent_type == "record":
            return InteractionDataHandler._prepare_record(query, user_id, db, language)
        elif intent_type == "edit":
            return InteractionDataHandler._prepare_edit(query, user_id, db, language)
        elif intent_type == "delete":
            return InteractionDataHandler._prepare_delete(query, user_id, db, language)
        elif intent_type == "transfer":
            return InteractionDataHandler._prepare_transfer(
                query, user_id, db, language
            )
        elif intent_type == "goal":
            return InteractionDataHandler._prepare_goal(query, user_id, db, language)
        else:
            return {
                "success": False,
                "reason": f"Unknown interaction type: {intent_type}",
            }

    @staticmethod
    def _prepare_record(query: str, user_id: int, db, language: str) -> Dict[str, Any]:
        """Prepare for recording a transaction"""
        return {
            "success": True,
            "action": "record",
            "requires_llm_parsing": True,
            "required_fields": ["amount", "category", "type"],
            "optional_fields": ["description", "date", "account_id"],
            "validation_rules": {
                "amount": "Must be positive number",
                "category": "Must be valid category from user's list",
                "type": "Must be 'income' or 'expense'",
            },
            "requires_confirmation": True,
            "confirmation_message": "Konfirmasi pencatatan transaksi?"
            if language == "id"
            else "Confirm recording transaction?",
            "audit": True,  # Log untuk audit trail
            "next_step": "llm_executor",
        }

    @staticmethod
    def _prepare_edit(query: str, user_id: int, db, language: str) -> Dict[str, Any]:
        """Prepare for editing a transaction"""
        return {
            "success": True,
            "action": "edit",
            "requires_llm_parsing": True,
            "required_fields": ["transaction_id", "field_to_edit"],
            "optional_fields": ["new_value"],
            "validation_rules": {
                "transaction_id": "Transaction must exist and belong to user",
                "field_to_edit": "Must be editable field (amount, category, date)",
            },
            "requires_confirmation": True,
            "confirmation_message": "Konfirmasi perubahan transaksi?"
            if language == "id"
            else "Confirm transaction edit?",
            "audit": True,
            "next_step": "llm_executor",
        }

    @staticmethod
    def _prepare_delete(query: str, user_id: int, db, language: str) -> Dict[str, Any]:
        """Prepare for deleting a transaction"""
        return {
            "success": True,
            "action": "delete",
            "requires_llm_parsing": True,
            "required_fields": ["transaction_id"],
            "validation_rules": {
                "transaction_id": "Transaction must exist and belong to user",
            },
            "requires_confirmation": True,
            "requires_user_password": True,  # Extra security for delete
            "confirmation_message": "Konfirmasi PENGHAPUSAN transaksi? Ini tidak dapat dibatalkan!"
            if language == "id"
            else "CONFIRM DELETE? This cannot be undone!",
            "audit": True,
            "next_step": "llm_executor",
        }

    @staticmethod
    def _prepare_transfer(
        query: str, user_id: int, db, language: str
    ) -> Dict[str, Any]:
        """Prepare for transferring between accounts"""
        return {
            "success": True,
            "action": "transfer",
            "requires_llm_parsing": True,
            "required_fields": ["from_account", "to_account", "amount"],
            "optional_fields": ["description", "date"],
            "validation_rules": {
                "from_account": "Account must exist and belong to user",
                "to_account": "Account must exist and belong to user",
                "amount": "Amount must be positive and <= from_account balance",
            },
            "requires_confirmation": True,
            "confirmation_message": "Konfirmasi transfer?"
            if language == "id"
            else "Confirm transfer?",
            "audit": True,
            "next_step": "llm_executor",
        }

    @staticmethod
    def _prepare_goal(query: str, user_id: int, db, language: str) -> Dict[str, Any]:
        """Prepare for creating/updating savings goal"""
        return {
            "success": True,
            "action": "goal",
            "requires_llm_parsing": True,
            "required_fields": ["goal_name", "target_amount"],
            "optional_fields": ["target_date", "current_amount"],
            "validation_rules": {
                "goal_name": "Must be descriptive",
                "target_amount": "Must be positive number",
                "target_date": "Should be in future if provided",
            },
            "requires_confirmation": True,
            "confirmation_message": "Konfirmasi pembuatan saving goal?"
            if language == "id"
            else "Confirm creating savings goal?",
            "audit": True,
            "next_step": "llm_executor",
        }

    @staticmethod
    def validate_user_permission(
        user_id: int, resource_id: int, resource_type: str, db
    ) -> bool:
        """Validate that user owns the resource they're trying to modify"""
        if resource_type == "transaction":
            cur = db.execute(
                "SELECT user_id FROM transactions WHERE id = ?", (resource_id,)
            )
            row = cur.fetchone()
            return row and row["user_id"] == user_id
        elif resource_type == "account":
            cur = db.execute(
                "SELECT user_id FROM accounts WHERE id = ?", (resource_id,)
            )
            row = cur.fetchone()
            return row and row["user_id"] == user_id
        return False
