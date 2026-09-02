"""procure_ai subgraph: new-project intake via Project Initiator create_agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent_server.core.state import MateAgentState
from agent_server.core.subagents.procure_agent.nodes.project_initiator import (
    normalize_reply,
    parse_draft,
    project_initiator_agent,
)
from shared.logger_global import get_logger

log = get_logger(__name__, service="agent_server")

_builder = StateGraph(MateAgentState)
_builder.add_node("project_initiator", project_initiator_agent)
_builder.add_node("normalize_reply", normalize_reply)
_builder.add_node("parse_draft", parse_draft)
_builder.add_edge(START, "project_initiator")
_builder.add_edge("project_initiator", "normalize_reply")
_builder.add_edge("normalize_reply", "parse_draft")
_builder.add_edge("parse_draft", END)

procure_ai = _builder.compile(name="procure_ai")
log.info("procure_ai subgraph compiled")
