"""Knowledge graph node. Fan-out sibling of kb_build — same chunks, different artefact."""

from __future__ import annotations

from typing import Any, Optional

import mlflow
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.procurement_ai.capabilities import project_id_from_state
from ai_brain.core.procurement_ai.pipeline import persist_kg
from ai_brain.core.procurement_ai.project_context import load_context


@mlflow.trace(name="procura_kg_build", span_type=SpanType.CHAIN)
def kg_build(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    project_id = project_id_from_state(state)
    if not project_id:
        return {"procurement": {"kg_status": "blocked", "kg_error": "project_id missing"}}
    project, artifacts, chunks = load_context(project_id)
    if project is None:
        return {"procurement": {"kg_status": "blocked", "kg_error": "project not found"}}
    payload = persist_kg(project_id, project, artifacts, chunks)
    return {
        "procurement": {
            "kg_status": payload.get("status") or "ready",
            "kg_nodes": payload.get("node_count"),
            "kg_edges": payload.get("edge_count"),
        }
    }
