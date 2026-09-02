"""Project Initiator — LangChain create_agent harness for new-project intake."""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from agent_server.core.context.prompts import load_prompt
from agent_server.core.message_text import normalize_assistant_message, visible_text_from_message
from agent_server.core.model_factory import get_llm
from agent_server.core.state import MateAgentState, ProjectDraft
from agent_server.core.subagents.procure_agent.draft import (
    question_for_reason,
    split_visible_and_draft,
    validate_draft,
)
from shared.logger_global import get_logger

log = get_logger(__name__, service="agent_server")

_SYSTEM_PROMPT = load_prompt("proj_initiator.md")

project_initiator_agent = create_agent(
    model=get_llm(),
    tools=[],
    system_prompt=_SYSTEM_PROMPT,
    state_schema=MateAgentState,
    name="project_initiator",
)
log.info("project initiator create_agent compiled")


def _last_ai_message(state: MateAgentState) -> Any:
    messages = state.get("messages") or []
    for msg in reversed(messages):
        role = getattr(msg, "type", None)
        if role is None and isinstance(msg, dict):
            role = msg.get("role")
        if role in {"ai", "assistant"}:
            return msg
    return None


def _last_ai_text(state: MateAgentState) -> str:
    msg = _last_ai_message(state)
    if msg is None:
        return ""
    return visible_text_from_message(msg)


def normalize_reply(state: MateAgentState) -> dict[str, Any]:
    """Rewrite list-shaped AIMessage content to str before checkpointing."""
    messages = list(state.get("messages") or [])
    if not messages:
        return {}

    updated = False
    for index in range(len(messages) - 1, -1, -1):
        msg = messages[index]
        role = getattr(msg, "type", None)
        if role is None and isinstance(msg, dict):
            role = msg.get("role")
        if role not in {"ai", "assistant"}:
            continue
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if isinstance(content, str):
            break
        messages[index] = normalize_assistant_message(msg)
        updated = True
        break

    if not updated:
        return {}
    return {"messages": messages}


def parse_draft(state: MateAgentState) -> dict[str, Any]:
    """Lift the JSON trailer into project_draft without rewriting messages."""
    ai_text = _last_ai_text(state)
    visible, draft = split_visible_and_draft(ai_text)
    thread_id = str(state.get("thread_id") or "")

    if draft is None:
        log.info("draft_rejected reason=parse_failed thread={}", thread_id)
        result: dict[str, Any] = {
            "draft_status": "rejected",
            "draft_reason": "parse_failed",
        }
        if visible:
            result["visible_reply"] = visible
        return result

    merged: ProjectDraft = dict(state.get("project_draft") or {})
    for key, value in draft.items():
        if value in ("", [], None):
            continue
        merged[key] = value

    validation = validate_draft(merged)
    base: dict[str, Any] = {"visible_reply": visible} if visible else {}
    if validation.ok:
        log.info(
            "draft_accepted name={} workflow={} thread={}",
            merged.get("name") or "",
            merged.get("workflowEntryPoint") or "",
            thread_id,
        )
        return {
            **base,
            "project_draft": merged,
            "draft_status": "accepted",
            "draft_reason": "",
        }

    log.info(
        "draft_rejected reason={} thread={}",
        validation.reason,
        thread_id,
    )
    result = {
        **base,
        "project_draft": merged,
        "draft_status": "rejected",
        "draft_reason": validation.reason,
    }
    question = question_for_reason(validation.reason)
    if question:
        result["draft_question"] = question
    return result
