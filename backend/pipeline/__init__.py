"""Pipeline package for chat orchestration

This package contains:
- manager: ChatPipelineManager for orchestrating intent classification and routing
"""

from .manager import ChatPipelineManager

__all__ = ["ChatPipelineManager"]
