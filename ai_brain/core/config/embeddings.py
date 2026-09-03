"""Embedding model id. Separate from chat LLM import/auth — swap the pointer in llm.yaml."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

_LLM_YAML = Path(__file__).with_name("llm.yaml")
PLACEHOLDER_NAME = "databricks-embedding-placeholder"


@lru_cache(maxsize=1)
def get_embedding_model_name() -> str:
    """Return the Databricks embedding endpoint name.

    Override with ``DATABRICKS_EMBEDDING_MODEL``. Until that pointer exists,
    ``llm.yaml`` ships ``databricks-embedding-placeholder``.
    """
    override = os.getenv("DATABRICKS_EMBEDDING_MODEL", "").strip()
    if override:
        return override
    with _LLM_YAML.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    models = data.get("models") or {}
    name = models.get("embedding_model") or PLACEHOLDER_NAME
    return str(name)
