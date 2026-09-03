from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import mlflow
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.utils.content import content_text


@lru_cache(maxsize=1)
def get_procura_main_agent():
    from langchain.agents import create_agent

    from ai_brain.core.config import get_llm
    from ai_brain.core.utils import read_prompt

    return create_agent(
        model=get_llm(),
        tools=[],
        system_prompt=read_prompt("procura_main_agent.md"),
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
    )
    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    text = content_text(getattr(last, "content", "") if last is not None else "")
    return {"procurement": {"main_agent": text}}
