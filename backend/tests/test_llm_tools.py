"""Structural checks for LLM tool definitions to catch regressions early."""

from llm import TOOLS_DEFINITIONS


REQUIRED_FUNCTION_KEYS = {"name", "description", "parameters"}


def test_tools_list_not_empty():
    assert TOOLS_DEFINITIONS, "TOOLS_DEFINITIONS should not be empty"


def test_tool_names_unique():
    names = [tool["function"]["name"] for tool in TOOLS_DEFINITIONS]
    assert len(names) == len(set(names)), "Tool names must be unique"


def test_tool_schema_minimum_keys():
    for tool in TOOLS_DEFINITIONS:
        fn = tool.get("function", {})
        assert REQUIRED_FUNCTION_KEYS.issubset(fn.keys())
        params = fn.get("parameters", {})
        assert params.get("type") == "object"
        assert "properties" in params


def test_tool_parameters_have_required_fields():
    for tool in TOOLS_DEFINITIONS:
        params = tool["function"].get("parameters", {})
        required = params.get("required", [])
        # All required fields should be part of properties
        if required:
            props = params.get("properties", {})
            assert all(field in props for field in required)
