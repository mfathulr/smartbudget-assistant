"""
Chat Pipeline Manager
Mengorkestrasikan intent classification, routing, dan execution.
"""

from typing import Dict, Any
from services import IntentClassifier


class ChatPipelineManager:
    """Main orchestrator for the enhanced chatbot pipeline"""

    def __init__(self, db, user_id: int, language: str = "id"):
        self.db = db
        self.user_id = user_id
        self.language = language
        self.pipeline_log = []

    def process_query(
        self, query: str, year: int = None, month: int = None
    ) -> Dict[str, Any]:
        """
        Process user query through the modular pipeline.

        Pipeline Flow:
        1. Intent Classification
        2. Route to appropriate handler
        3. Get validation/context/response
        4. Return with metadata for frontend/LLM

        Returns:
            Dict with response, routing info, and metadata
        """
        from datetime import datetime

        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month

        # Step 1: Intent Classification
        print(f"[PIPELINE] Processing query: {query}")
        intent_category, intent_type, confidence = IntentClassifier.classify(query)
        self._log(
            f"Intent classified: {intent_category}/{intent_type} (confidence: {confidence})"
        )

        # Step 2: Route to handler
        result = self._route_to_handler(
            query, intent_category, intent_type, confidence, year, month
        )

        # Attach intent metadata for downstream LLM prompt shaping
        result["intent_category"] = intent_category
        result["intent_type"] = intent_type
        result["intent_confidence"] = confidence
        result["pipeline_log"] = self.pipeline_log
        return result

    def _route_to_handler(
        self,
        query: str,
        intent_category: str,
        intent_type: str,
        confidence: float,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """Route query to appropriate handler based on intent"""

        try:
            if intent_category == "general":
                return self._handle_general(query, intent_type, confidence)

            elif intent_category == "context_data":
                return self._handle_context_data(
                    query, intent_type, confidence, year, month
                )

            elif intent_category == "interaction_data":
                return self._handle_interaction_data(query, intent_type, confidence)

            else:
                return {
                    "success": False,
                    "error": f"Unknown intent category: {intent_category}",
                }

        except Exception as e:
            self._log(f"Error in pipeline: {str(e)}")
            return {
                "success": False,
                "error": f"Pipeline error: {str(e)}",
                "fallback_to_llm": True,
            }

    def _handle_general(
        self, query: str, intent_type: str, confidence: float
    ) -> Dict[str, Any]:
        """Handle general query - always use LLM without data context"""
        self._log("Routing to General Handler - LLM without data context")

        # General: Direct answer, no tools/data query
        prompt_hint = (
            "Answer briefly. Focus on fundamentals. No tools."
            if intent_type == "education"
            else "Answer briefly as FIN. No tools."
        )

        return {
            "success": False,
            "fallback_to_llm": True,
            "requires_context": False,
            "requires_data_query": False,
            "prompt_hint": prompt_hint,
            "response_type": "general",
        }

    def _handle_context_data(
        self, query: str, intent_type: str, confidence: float, year: int, month: int
    ) -> Dict[str, Any]:
        """Handle context data query - LLM with data context"""
        self._log(
            f"Routing to Context Data Handler ({intent_type}) - LLM with data context"
        )

        # Context: Query data first, then answer
        prompt_hint = (
            "1. Use tools: get_summary/get_balance/get_transactions\n"
            "2. Ask if missing: year/month/account\n"
            "3. Answer with context"
        )

        return {
            "success": False,
            "fallback_to_llm": True,
            "requires_context": True,
            "requires_data_query": True,
            "prompt_hint": prompt_hint,
            "response_type": "context_data",
            "year": year,
            "month": month,
        }

    def _handle_interaction_data(
        self, query: str, intent_type: str, confidence: float
    ) -> Dict[str, Any]:
        """Handle interaction data request - LLM with data context and validation"""
        self._log(
            f"Routing to Interaction Data Handler ({intent_type}) - LLM with validation"
        )

        # Interaction: Validate → Confirm → Execute
        prompt_hint = (
            "1. Collect: amount/category/account/date\n"
            "2. Confirm with user\n"
            "3. Validate then call tool: add_transaction/transfer_funds/create_goal"
        )

        return {
            "success": False,
            "fallback_to_llm": True,
            "requires_context": True,
            "requires_data_query": True,
            "requires_validation": True,
            "prompt_hint": prompt_hint,
            "response_type": "interaction_data",
        }

    def _log(self, message: str) -> None:
        """Add log entry"""
        self.pipeline_log.append(message)
        print(f"[PIPELINE LOG] {message}")
