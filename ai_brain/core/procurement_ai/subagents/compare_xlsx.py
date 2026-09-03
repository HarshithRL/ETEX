from __future__ import annotations

from typing import Any, Optional

import mlflow
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.procurement_ai.capabilities import project_id_from_state
from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.packs.compare_xlsx import build_comparison_xlsx
from ai_brain.core.procurement_ai.project_context import load_context


@mlflow.trace(name="procura_compare_xlsx", span_type=SpanType.TOOL)
async def compare_xlsx(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    project_id = project_id_from_state(state)
    if not project_id:
        return {
            "procurement": {
                "compare_xlsx": "project_id missing",
                "xlsx_status": "blocked",
            }
        }
    project, artifacts, chunks = load_context(project_id)
    if project is None:
        return {
            "procurement": {
                "compare_xlsx": "project not found",
                "xlsx_status": "blocked",
            }
        }
    insights = build_insight_payload(project, artifacts, chunks)
    thread_id = ""
    if isinstance(config, dict):
        thread_id = str((config.get("configurable") or {}).get("thread_id") or "")
    result = build_comparison_xlsx(
        project_id,
        insights,
        thread_id=thread_id,
        chunks=chunks,
        artifacts=artifacts,
    )
    return {
        "procurement": {
            "compare_xlsx": result.get("status"),
            "xlsx_status": result.get("status"),
            "xlsx_href": result.get("href") or "",
        }
    }
