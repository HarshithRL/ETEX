"""AI Brain configuration."""

from .llm import (
    get_fast_llm,
    get_fast_model_name,
    get_llm,
    get_thinking_llm,
    get_thinking_model_name,
    get_workspace_client,
)

__all__ = [
    "get_fast_llm",
    "get_fast_model_name",
    "get_llm",
    "get_thinking_llm",
    "get_thinking_model_name",
    "get_workspace_client",
]
