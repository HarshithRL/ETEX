from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

import mlflow
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.procurement_ai.capabilities import project_id_from_state
from ai_brain.core.procurement_ai.knowledge import knowledge_prompt_block
from ai_brain.core.utils import read_prompt
from ai_brain.core.utils.content import content_text


@dataclass
class ProcuraContext:
    project_id: str = ""


def _context_project_id(context: Any) -> str:
    if context is None:
        return ""
    if isinstance(context, dict):
        return str(context.get("project_id") or "").strip()
    return str(getattr(context, "project_id", "") or "").strip()


def project_id_for_agent(state: dict[str, Any], config: RunnableConfig | None) -> str:
    project_id = project_id_from_state(state)
    if project_id:
        return project_id
    if isinstance(config, dict):
        return str((config.get("configurable") or {}).get("thread_id") or "").strip()
    return ""


def _runtime_project_id(request: ModelRequest) -> str:
    runtime = getattr(request, "runtime", None)
    project_id = _context_project_id(getattr(runtime, "context", None) if runtime else None)
    if project_id:
        return project_id
    config = getattr(runtime, "config", None) if runtime else None
    if isinstance(config, dict):
        return str((config.get("configurable") or {}).get("thread_id") or "").strip()
    return ""


def _last_user_text(messages: Any) -> str:
    for message in reversed(list(messages or [])):
        if isinstance(message, dict):
            role = str(message.get("role") or message.get("type") or "")
            content = message.get("content")
        else:
            role = str(getattr(message, "type", "") or getattr(message, "role", "") or "")
            content = getattr(message, "content", "")
        if role in {"user", "human"}:
            return content_text(content)
    return ""


@dynamic_prompt
def procura_kb_prompt(request: ModelRequest) -> str:
    """Inject ranked project-file excerpts so create_agent can cite the KB without tools."""
    base = read_prompt("procura_main_agent.md")
    project_id = _runtime_project_id(request)
    query = _last_user_text(getattr(request, "messages", None))
    block = knowledge_prompt_block(project_id, query)
    if not block:
        return base
    return f"{base}\n\n{block}"


@lru_cache(maxsize=1)
def get_procura_main_agent():
    from langchain.agents import create_agent

    from ai_brain.core.config import get_llm

    return create_agent(
        model=get_llm(),
        tools=[],
        middleware=[procura_kb_prompt],
        context_schema=ProcuraContext,
    )


procura_main_agent = None


@mlflow.trace(name="procura_main_agent", span_type=SpanType.AGENT)
async def main_agent(
    state: dict[str, Any],
    # LangGraph matches this annotation literally; ``RunnableConfig | None``
    # is rejected and config is then never injected.
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    # LangChain: pass parent RunnableConfig into nested ainvoke so callbacks
    # (MlflowLangchainTracer) and token streaming propagate.
    project_id = project_id_for_agent(state, config)
    result = await get_procura_main_agent().ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": state.get("request") or "Hello",
                }
            ],
        },
        config=config,
        context=ProcuraContext(project_id=project_id),
    )
    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    text = content_text(getattr(last, "content", "") if last is not None else "")
    return {"procurement": {"main_agent": text}}
