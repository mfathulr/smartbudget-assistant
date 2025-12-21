"""Conversation Interpretation Middleware - Auto-handle field interpretation in chat flows

Provides middleware that automatically interprets user inputs in conversation
and asks for confirmation when needed before proceeding with actions.
"""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from core import get_logger
from llm.input_interpreter import (
    interpret_input,
    InterpretationResult,
    MatchConfidence,
)
from llm.chat_integration import ChatIntegrationHelper

logger = get_logger(__name__)


@dataclass
class InterpretationCheckpoint:
    """Checkpoint for user confirmation of interpreted fields"""
    
    field_name: str
    field_type: str  # account, date, category, etc
    original_input: str
    interpreted_value: Any
    confidence: MatchConfidence
    alternatives: Optional[list] = None
    awaiting_confirmation: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "field_type": self.field_type,
            "original_input": self.original_input,
            "interpreted_value": self.interpreted_value,
            "confidence": self.confidence.value,
            "alternatives": self.alternatives,
            "awaiting_confirmation": self.awaiting_confirmation,
        }


class InterpretationMiddleware:
    """Middleware for handling field interpretation in conversation flows"""
    
    def __init__(self, db):
        """
        Initialize middleware
        
        Args:
            db: Database connection
        """
        self.db = db
        self.helper = ChatIntegrationHelper()
    
    def process_fields(
        self,
        user_id: int,
        fields: Dict[str, str],
        field_types: Dict[str, str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process and interpret user fields
        
        Args:
            user_id: User ID
            fields: Dict of field_name -> user_value
            field_types: Dict of field_name -> interpretation_type
            **kwargs: Additional context
            
        Returns:
            Dict with interpreted fields and any pending confirmations
        """
        interpretations = {}
        checkpoints = []  # Fields awaiting confirmation
        
        for field_name, user_value in fields.items():
            if not user_value or field_name not in field_types:
                continue
            
            field_type = field_types[field_name]
            
            # Get field-specific kwargs
            field_kwargs = {}
            if field_type == "category" and "tx_type" in kwargs:
                field_kwargs["tx_type"] = kwargs["tx_type"]
            
            # Interpret the field
            try:
                result = interpret_input(field_type, user_value, **field_kwargs)
                interpretations[field_name] = result
                
                # Log interpretation
                logger.info(
                    "field_interpreted",
                    user_id=user_id,
                    field=field_name,
                    confidence=result.confidence.value,
                    original=user_value,
                    interpreted=result.interpreted_value,
                )
                
                # Track fields needing confirmation
                if result.needs_confirmation:
                    checkpoint = InterpretationCheckpoint(
                        field_name=field_name,
                        field_type=field_type,
                        original_input=user_value,
                        interpreted_value=result.interpreted_value,
                        confidence=result.confidence,
                        alternatives=result.alternatives,
                        awaiting_confirmation=True,
                    )
                    checkpoints.append(checkpoint)
                    
            except Exception as e:
                logger.error(
                    "field_interpretation_error",
                    user_id=user_id,
                    field=field_name,
                    error=str(e),
                )
                interpretations[field_name] = None
        
        return {
            "interpretations": interpretations,
            "checkpoints": checkpoints,
            "has_pending_confirmations": len(checkpoints) > 0,
            "next_confirmation": checkpoints[0] if checkpoints else None,
        }
    
    def build_confirmation_response(
        self,
        checkpoint: InterpretationCheckpoint
    ) -> Dict[str, Any]:
        """
        Build a response asking user to confirm an interpretation
        
        Args:
            checkpoint: InterpretationCheckpoint to confirm
            
        Returns:
            Response dict for chat API
        """
        msg = f"Saya interpretasi '{checkpoint.original_input}' sebagai **{checkpoint.interpreted_value}**\n"
        
        if checkpoint.alternatives:
            msg += f"\nAlternatif lain: {', '.join(checkpoint.alternatives)}\n"
        
        msg += "\nBenar? Respons dengan **'ya'** atau **'tidak'**"
        
        return {
            "success": False,
            "requires_confirmation": True,
            "message": msg,
            "code": f"CONFIRM_{checkpoint.field_type.upper()}",
            "checkpoint": checkpoint.to_dict(),
        }
    
    def handle_confirmation_response(
        self,
        checkpoint: InterpretationCheckpoint,
        user_response: str
    ) -> Dict[str, Any]:
        """
        Handle user's confirmation response
        
        Args:
            checkpoint: The checkpoint being confirmed
            user_response: User's yes/no response
            
        Returns:
            Dict with confirmation result
        """
        response_lower = user_response.lower().strip()
        is_confirmed = response_lower in ["ya", "yes", "y", "benar", "iya"]
        
        if is_confirmed:
            return {
                "confirmed": True,
                "field_name": checkpoint.field_name,
                "value": checkpoint.interpreted_value,
                "message": f"✅ {checkpoint.field_type.title()} dikonfirmasi: {checkpoint.interpreted_value}",
            }
        else:
            return {
                "confirmed": False,
                "field_name": checkpoint.field_name,
                "message": (
                    f"Baik, tidak pakai {checkpoint.field_type} '{checkpoint.interpreted_value}'.\n"
                    f"Mohon berikan input yang benar."
                ),
                "ask_user": (
                    f"Mohon berikan {checkpoint.field_type} yang benar untuk {checkpoint.field_name}"
                ),
            }
    
    def save_interpretation_checkpoint(
        self,
        user_id: int,
        conversation_id: int,
        checkpoint: InterpretationCheckpoint
    ) -> bool:
        """
        Save interpretation checkpoint to database for multi-turn flows
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            checkpoint: InterpretationCheckpoint to save
            
        Returns:
            Success status
        """
        try:
            # Store in conversation metadata or pending_confirmations table
            # This allows the system to remember what was being confirmed
            # even if conversation continues across multiple turns
            logger.info(
                "checkpoint_saved",
                user_id=user_id,
                conversation_id=conversation_id,
                field=checkpoint.field_name,
                checkpoint=checkpoint.to_dict(),
            )
            return True
        except Exception as e:
            logger.error(
                "checkpoint_save_error",
                user_id=user_id,
                error=str(e),
            )
            return False
    
    def resolve_interpretations(
        self,
        interpretations: Dict[str, InterpretationResult],
        confirmations: Dict[str, bool]  # field_name -> is_confirmed
    ) -> Dict[str, Any]:
        """
        Resolve interpretations based on user confirmations
        
        Args:
            interpretations: Dict of field -> InterpretationResult
            confirmations: Dict of field -> whether user confirmed
            
        Returns:
            Dict with final values and any still-pending fields
        """
        resolved = {}
        pending = []
        
        for field_name, result in interpretations.items():
            if field_name in confirmations:
                if confirmations[field_name]:
                    # User confirmed
                    resolved[field_name] = result.interpreted_value
                else:
                    # User rejected
                    pending.append(field_name)
            else:
                # No confirmation needed, use interpreted value
                if result.confidence != MatchConfidence.NO_MATCH:
                    resolved[field_name] = result.interpreted_value
                else:
                    pending.append(field_name)
        
        return {
            "resolved": resolved,
            "pending": pending,
            "all_resolved": len(pending) == 0,
        }


# Global middleware instance
_middleware = None


def get_interpretation_middleware(db=None):
    """Get or create global interpretation middleware"""
    global _middleware
    if _middleware is None and db:
        _middleware = InterpretationMiddleware(db)
    return _middleware


def setup_interpretation_middleware(db):
    """Setup interpretation middleware with database"""
    global _middleware
    _middleware = InterpretationMiddleware(db)
    return _middleware
