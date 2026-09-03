"""Join node after parallel KB + knowledge graph."""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.runnables import RunnableConfig


def kb_ready(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    procurement = state.get("procurement") or {}
    kb = procurement.get("kb_status") or "empty"
    kg = procurement.get("kg_status") or "empty"
    stage = "packs_hitl" if kb != "blocked" and kg != "blocked" else "blocked"
    return {
        "procurement": {
            "pipeline_stage": stage,
            "kb_kg_joined": True,
        }
    }
