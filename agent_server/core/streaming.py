"""Normalize LangGraph astream chunks into UI SSE events."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from agent_server.core.message_text import (
    latest_assistant_text,
    reasoning_text_from_message,
    visible_text_from_message,
)
from agent_server.core.state import TokenUsage
from agent_server.core.subagents.procure_agent.draft import (
    DRAFT_FENCE_START,
    draft_has_meaningful_fields,
    question_for_reason,
    split_visible_and_draft,
    validate_draft,
)

_USAGE_KEYS = ("input_tokens", "output_tokens", "total_tokens")

_SHOW_REASONING = os.getenv("MATE_SHOW_REASONING", "").strip().lower() in {
    "1",
    "true",
    "yes",
} or os.getenv("MATE_ENV", "dev").lower() != "prod"

_FALLBACK_REPLY = "I could not generate a reply. Please try again."


def _chunk_as_v2(chunk: Any) -> tuple[str, tuple, Any] | None:
    if isinstance(chunk, dict) and "type" in chunk:
        return str(chunk.get("type") or ""), tuple(chunk.get("ns") or ()), chunk.get("data")
    if isinstance(chunk, tuple) and len(chunk) == 3:
        mode, ns, data = chunk
        return str(mode), tuple(ns or ()), data
    if isinstance(chunk, tuple) and len(chunk) == 2:
        first, second = chunk
        if isinstance(first, str):
            return first, (), second
        return "messages", tuple(first or ()), second
    return None


def _usage_from_message(msg: Any) -> TokenUsage | None:
    meta = getattr(msg, "usage_metadata", None)
    if meta is None and isinstance(msg, dict):
        meta = msg.get("usage_metadata")
    if not isinstance(meta, dict):
        return None
    usage: TokenUsage = {}
    for key in _USAGE_KEYS:
        value = meta.get(key)
        if isinstance(value, int):
            usage[key] = value
    return usage or None


def _node_from_updates(data: Any) -> str | None:
    if not isinstance(data, dict) or not data:
        return None
    return next(iter(data.keys()), None)


def _message_payload(data: Any) -> tuple[Any, dict]:
    if isinstance(data, tuple) and len(data) == 2:
        return data[0], data[1] if isinstance(data[1], dict) else {}
    return data, {}


def _merge_assembled(current: str, candidate: str) -> str:
    """Prefer the longer assistant text when updates carry the full message."""
    if not candidate:
        return current
    if not current:
        return candidate
    if candidate.startswith(current) or len(candidate) >= len(current):
        return candidate
    return current


def _emit_reasoning(thought: str) -> list[dict[str, Any]]:
    if not thought or not _SHOW_REASONING:
        return []
    return [
        {"type": "reasoning", "text": thought},
        {"type": "thought", "text": thought},
    ]


def _yield_draft_event(draft: dict[str, Any]) -> dict[str, Any] | None:
    if draft_has_meaningful_fields(draft):
        return {"type": "draft", **draft}
    return None


async def iter_sse_events(
    stream: AsyncIterator[Any],
) -> AsyncIterator[dict[str, Any]]:
    assembled = ""
    hiding_draft = False
    last_usage: TokenUsage | None = None
    accepted_draft = None
    last_question = ""
    last_draft_reason = ""
    last_partial_draft: dict[str, Any] | None = None

    async for chunk in stream:
        parsed = _chunk_as_v2(chunk)
        if parsed is None:
            continue
        mode, _ns, data = parsed

        if mode == "updates":
            node = _node_from_updates(data)
            if node:
                yield {"type": "updates", "node": str(node)}
            if isinstance(data, dict):
                for node_name, payload in data.items():
                    if not isinstance(payload, dict):
                        continue
                    visible_reply = str(payload.get("visible_reply") or "").strip()
                    if visible_reply:
                        assembled = _merge_assembled(assembled, visible_reply)
                    messages = payload.get("messages")
                    if messages:
                        assembled = _merge_assembled(
                            assembled,
                            latest_assistant_text(messages),
                        )
                    draft = payload.get("project_draft")
                    if isinstance(draft, dict):
                        last_partial_draft = draft
                        draft_event = _yield_draft_event(draft)
                        if draft_event:
                            yield draft_event
                        if payload.get("draft_status") == "accepted":
                            accepted_draft = draft

                    draft_status = payload.get("draft_status")
                    draft_reason = str(payload.get("draft_reason") or "")
                    if draft_reason:
                        last_draft_reason = draft_reason
                    if draft_status == "rejected" and draft_reason in {
                        "empty_name",
                        "missing_workflow",
                    }:
                        question = str(payload.get("draft_question") or "") or question_for_reason(
                            draft_reason  # type: ignore[arg-type]
                        )
                        if question:
                            last_question = question
                            yield {"type": "question", "text": question}

                    if visible_reply and node_name == "parse_draft":
                        yield {"type": "token", "text": visible_reply, "replace": True}

                    usage = payload.get("usage")
                    if isinstance(usage, dict) and usage:
                        last_usage = usage
                        yield {"type": "usage", **usage}
            continue

        if mode != "messages":
            continue

        msg, _meta = _message_payload(data)
        for event in _emit_reasoning(reasoning_text_from_message(msg)):
            yield event

        usage = _usage_from_message(msg)
        if usage:
            last_usage = usage
            yield {"type": "usage", **usage}

        piece = visible_text_from_message(msg)
        if not piece:
            continue
        assembled += piece
        if hiding_draft:
            continue
        fence_at = assembled.find(DRAFT_FENCE_START)
        if fence_at != -1:
            hiding_draft = True
            visible_piece = piece[: max(0, len(piece) - (len(assembled) - fence_at))]
            if visible_piece:
                yield {"type": "token", "text": visible_piece}
            continue
        yield {"type": "token", "text": piece}

    visible, draft = split_visible_and_draft(assembled)
    if draft is None and last_partial_draft is not None:
        draft = last_partial_draft
    if draft:
        draft_event = _yield_draft_event(draft)
        if draft_event:
            yield draft_event
        if validate_draft(draft).ok:
            accepted_draft = draft

    text = visible.strip()
    if not text:
        text = last_question
    if not text and last_draft_reason:
        text = question_for_reason(last_draft_reason)  # type: ignore[arg-type]
    if not text and draft is not None:
        validation = validate_draft(draft)
        if not validation.ok:
            text = question_for_reason(validation.reason)  # type: ignore[arg-type]
    if not text:
        text = _FALLBACK_REPLY

    done: dict[str, Any] = {"type": "done", "role": "ai", "text": text}
    if last_usage:
        done["usage"] = last_usage
    if accepted_draft:
        done["draft"] = accepted_draft
    yield done
