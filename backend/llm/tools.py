"""LLM tool definitions for OpenAI and Gemini"""

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "add_transaction",
            "description": "Add income/expense transaction",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["income", "expense"]},
                    "amount": {"type": "number"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "date": {"type": "string"},
                    "account": {"type": "string"},
                },
                "required": ["type", "amount", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_savings_goal",
            "description": "Create savings goal",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "target_amount": {"type": "number"},
                    "description": {"type": "string"},
                    "target_date": {"type": "string"},
                },
                "required": ["name", "target_amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_transaction",
            "description": "Update existing transaction",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "date": {"type": "string"},
                    "type": {"type": "string"},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "amount": {"type": "number"},
                    "account": {"type": "string"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_transaction",
            "description": "Delete transaction",
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "number"}},
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_funds",
            "description": "Transfer between accounts",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "from_account": {"type": "string"},
                    "to_account": {"type": "string"},
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["amount", "from_account", "to_account"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_savings_goal",
            "description": "Update savings goal",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "number"},
                    "name": {"type": "string"},
                    "target_amount": {"type": "number"},
                    "description": {"type": "string"},
                    "target_date": {"type": "string"},
                },
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_savings",
            "description": "Transfer to savings goal",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "from_account": {"type": "string"},
                    "goal_id": {"type": "number"},
                    "date": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["amount", "from_account", "goal_id"],
            },
        },
    },
]
