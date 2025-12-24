"""Pydantic schemas for validating LLM action arguments

Ensures type safety and prevents invalid arguments from reaching the executor.
"""

from __future__ import annotations
from typing import Optional, Literal, Union, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class AddTransactionSchema(BaseModel):
    """Validate arguments for add_transaction action"""

    type: Optional[Literal["income", "expense"]] = Field(
        None, description="Transaction type"
    )
    amount: Optional[float] = Field(
        None, gt=0, le=100_000_000_000, description="Transaction amount"
    )
    category: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Transaction category"
    )
    description: Optional[str] = Field(
        "", max_length=500, description="Transaction description"
    )
    date: Optional[str] = Field(
        None, description="Transaction date (ISO format or natural language)"
    )
    account: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Account name"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        """Amount must be positive"""
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        """Type must be income or expense"""
        if v is not None and v not in ["income", "expense"]:
            raise ValueError('Type must be "income" or "expense"')
        return v


class CreateSavingsGoalSchema(BaseModel):
    """Validate arguments for create_savings_goal action"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="Goal name"
    )
    target_amount: Optional[float] = Field(
        None, gt=0, le=100_000_000_000, description="Target amount"
    )
    target_date: Optional[str] = Field(
        None, description="Target date (ISO format or natural language)"
    )
    description: Optional[str] = Field(
        "", max_length=500, description="Goal description"
    )

    @field_validator("target_amount")
    @classmethod
    def validate_amount(cls, v):
        """Amount must be positive"""
        if v is not None and v <= 0:
            raise ValueError("Target amount must be greater than 0")
        return v


class UpdateTransactionSchema(BaseModel):
    """Validate arguments for update_transaction action"""

    id: Optional[int] = Field(None, gt=0, description="Transaction ID")
    type: Optional[Literal["income", "expense"]] = Field(
        None, description="New transaction type"
    )
    amount: Optional[float] = Field(
        None, gt=0, le=100_000_000_000, description="New amount"
    )
    category: Optional[str] = Field(
        None, min_length=1, max_length=100, description="New category"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="New description"
    )
    date: Optional[str] = Field(None, description="New date")
    account: Optional[str] = Field(
        None, min_length=1, max_length=100, description="New account"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        """Amount must be positive if provided"""
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class DeleteTransactionSchema(BaseModel):
    """Validate arguments for delete_transaction action"""

    id: Optional[int] = Field(None, gt=0, description="Transaction ID to delete")
    confirm: Optional[bool] = Field(False, description="Confirmation flag for deletion")


class TransferFundsSchema(BaseModel):
    """Validate arguments for transfer_funds action"""

    amount: Optional[float] = Field(
        None, gt=0, le=100_000_000_000, description="Transfer amount"
    )
    from_account: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Source account"
    )
    to_account: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Destination account"
    )
    date: Optional[str] = Field(None, description="Transfer date")
    description: Optional[str] = Field(
        "", max_length=500, description="Transfer description"
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        """Amount must be positive"""
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_different_accounts(self):
        """from_account and to_account must be different"""
        if (
            self.from_account
            and self.to_account
            and self.from_account.lower() == self.to_account.lower()
        ):
            raise ValueError("from_account and to_account must be different")
        return self


class UpdateSavingsGoalSchema(BaseModel):
    """Validate arguments for update_savings_goal action"""

    id: Optional[int] = Field(None, gt=0, description="Goal ID")
    name: Optional[str] = Field(
        None, min_length=1, max_length=200, description="New goal name"
    )
    target_amount: Optional[float] = Field(
        None, gt=0, le=100_000_000_000, description="New target amount"
    )
    target_date: Optional[str] = Field(None, description="New target date")
    description: Optional[str] = Field(
        None, max_length=500, description="New description"
    )


# Schema mapping
ACTION_SCHEMAS = {
    "add_transaction": AddTransactionSchema,
    "record_expense": AddTransactionSchema,
    "record_income": AddTransactionSchema,
    "add_expense": AddTransactionSchema,
    "add_income": AddTransactionSchema,
    "create_savings_goal": CreateSavingsGoalSchema,
    "update_transaction": UpdateTransactionSchema,
    "delete_transaction": DeleteTransactionSchema,
    "transfer_funds": TransferFundsSchema,
    "update_savings_goal": UpdateSavingsGoalSchema,
}


def validate_action_arguments(
    action_name: str, arguments: dict
) -> tuple[bool, Union[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Validate LLM action arguments using Pydantic schemas

    Args:
        action_name: Name of the action (e.g., 'add_transaction')
        arguments: Dictionary of arguments from LLM

    Returns:
        Tuple of (is_valid, data_or_errors)
        - If valid: (True, validated_dict)
        - If invalid: (False, list_of_error_dicts)
    """
    schema_class = ACTION_SCHEMAS.get(action_name)

    if not schema_class:
        return False, [{"loc": ("action",), "msg": f"Unknown action: {action_name}"}]

    try:
        # Validate using Pydantic
        validated = schema_class(**arguments)
        # Return as dict with only non-None values
        return True, validated.model_dump(exclude_none=True)
    except Exception as e:
        # Return validation errors
        if hasattr(e, "errors"):
            return False, e.errors()
        else:
            return False, [{"loc": ("general",), "msg": str(e)}]
