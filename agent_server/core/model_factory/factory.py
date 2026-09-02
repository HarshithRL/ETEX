"""Databricks chat model via AI Gateway (WorkspaceClient profile auth)."""

from __future__ import annotations

import os

from databricks.sdk import WorkspaceClient
from databricks_langchain import ChatDatabricks

from shared.logger_global import get_logger

log = get_logger(__name__, service="agent_server")

DEFAULT_PROFILE = "adb-7181820732839861"
DEFAULT_MODEL = "system.ai.claude-sonnet-5"
DEFAULT_MAX_TOKENS = 1024


def get_workspace_client() -> WorkspaceClient:
    """Build a WorkspaceClient from the Databricks CLI profile (no hardcoded tokens)."""
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", DEFAULT_PROFILE)
    log.debug("creating WorkspaceClient profile={}", profile)
    return WorkspaceClient(profile=profile)


def get_llm() -> ChatDatabricks:
    """
    ChatDatabricks pointed at Unity AI Gateway MLflow path.

    Routes to ``{host}/ai-gateway/mlflow/v1`` — same surface as:
    ``POST /ai-gateway/mlflow/v1/chat/completions``.
    """
    model = os.getenv("DATABRICKS_MODEL", DEFAULT_MODEL)
    max_tokens_raw = os.getenv("DATABRICKS_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
    try:
        max_tokens = int(max_tokens_raw)
    except ValueError:
        max_tokens = DEFAULT_MAX_TOKENS

    temperature_raw = os.getenv("DATABRICKS_TEMPERATURE")
    temperature: float | None = None
    if temperature_raw is not None and temperature_raw.strip() != "":
        temperature = float(temperature_raw)

    log.debug("creating ChatDatabricks model={} max_tokens={}", model, max_tokens)

    kwargs: dict = {
        "model": model,
        "workspace_client": get_workspace_client(),
        "use_ai_gateway": True,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    return ChatDatabricks(**kwargs)
