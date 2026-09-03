from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import mlflow
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.procurement_ai.capabilities import project_id_from_state
from ai_brain.core.utils.content import content_text


@lru_cache(maxsize=1)
def get_deep_agent():
    from deepagents import create_deep_agent

    from ai_brain.core.config import get_llm
    from ai_brain.core.procurement_ai.subagents.deep_tools import deep_agent_tools
    from ai_brain.core.utils import read_prompt

    return create_deep_agent(
        model=get_llm(),
        tools=deep_agent_tools(),
        system_prompt=read_prompt("procura_deep_agent.md"),
    )


def _extract_brief(state: dict[str, Any]) -> str:
    project_id = project_id_from_state(state)
    asked = (state.get("request") or "").strip() or "Extract comparison facts from parsed chunks. Cite or write missing. Save facts before you finish."
    if not project_id:
        return asked
    try:
        from ai_brain.core.procurement_ai.insights import build_insight_payload
        from ai_brain.core.procurement_ai.project_context import load_context
        from ai_brain.core.procurement_ai.subagents.deep_tools import _chunks_payload

        project, artifacts, chunks = load_context(project_id)
        if project is None:
            return f"{asked}\n\nproject_id={project_id} was not found."
        insights = build_insight_payload(project, artifacts, chunks)
        excerpts = _chunks_payload(project_id, limit=24)
        return (
            f"{asked}\n\n"
            f"project_id={project_id}\n"
            f"process_type={insights.get('process_type')}\n"
            f"vendors={[v.get('name') for v in insights.get('vendors') or []]}\n"
            f"missing={insights.get('decision', {}).get('blockers')}\n\n"
            f"Parsed excerpts (cite these; call list_project_chunks for more):\n"
            f"{excerpts}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"{asked}\n\nproject_id={project_id}\ncontext_error={exc.__class__.__name__}"


@mlflow.trace(name="procura_deep_agent", span_type=SpanType.AGENT)
async def deepagent(
    state: dict[str, Any],
    # LangGraph matches this annotation literally; ``RunnableConfig | None``
    # is rejected and config is then never injected.
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    # LangChain: pass parent RunnableConfig into nested ainvoke so callbacks
    # (MlflowLangchainTracer) and token streaming propagate.
    result = await get_deep_agent().ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": _extract_brief(state),
                }
            ],
        },
        config=config,
    )
    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    text = content_text(getattr(last, "content", "") if last is not None else "")
    return {"procurement": {"deep_agent": text, "pipeline_stage": "extracted"}}
