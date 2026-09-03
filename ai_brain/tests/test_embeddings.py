from __future__ import annotations

from ai_brain.core.config.embeddings import get_embedding_model_name


def test_embedding_model_placeholder(monkeypatch):
    monkeypatch.delenv("DATABRICKS_EMBEDDING_MODEL", raising=False)
    get_embedding_model_name.cache_clear()
    assert get_embedding_model_name() == "databricks-embedding-placeholder"


def test_embedding_model_env_override(monkeypatch):
    monkeypatch.setenv("DATABRICKS_EMBEDDING_MODEL", "catalog.schema.my_embed")
    get_embedding_model_name.cache_clear()
    assert get_embedding_model_name() == "catalog.schema.my_embed"
