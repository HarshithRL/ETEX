"""Compiled Mate agent graph — routes into vertical subgraphs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) in sys.path:
    sys.path.remove(str(_SCRIPT_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from shared.logger_global import get_logger, setup_logging

setup_logging(service="agent_server")

from agent_server.core.state import MateAgentState
from agent_server.core.subagents.procure_agent.graph import procure_ai

log = get_logger(__name__, service="agent_server")

_UNSUPPORTED_REPLY = (
    "This chat is wired for new-project intake. Open Create project → Chat "
    "with the procurement agent to continue."
)


def route_intent(state: MateAgentState) -> Literal["procure_ai", "unsupported"]:
    if state.get("route") == "new_project":
        return "procure_ai"
    return "unsupported"


def unsupported(state: MateAgentState) -> dict:
    return {"messages": [{"role": "ai", "content": _UNSUPPORTED_REPLY}]}


_checkpointer = InMemorySaver()
_builder = StateGraph(MateAgentState)
_builder.add_node("procure_ai", procure_ai)
_builder.add_node("unsupported", unsupported)
_builder.add_conditional_edges(
    START,
    route_intent,
    {"procure_ai": "procure_ai", "unsupported": "unsupported"},
)
_builder.add_edge("procure_ai", END)
_builder.add_edge("unsupported", END)

graph = _builder.compile(checkpointer=_checkpointer, name="mate")
log.info("mate agent graph compiled")


def main() -> None:
    log.info("agent graph smoke invoke started")
    result = graph.invoke(
        {
            "messages": [
                {"role": "user", "content": "We need insulation board for Benelux plants."},
            ],
            "route": "new_project",
        },
        config={"configurable": {"thread_id": "smoke-new-project"}},
    )
    messages = result.get("messages") or []
    last = messages[-1] if messages else None
    content = getattr(last, "content", None) if last is not None else None
    output = content if content is not None else result
    log.info("agent graph smoke invoke done")
    print(output)


if __name__ == "__main__":
    main()
