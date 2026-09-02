"""Invoke Mate create_agent for procurement workspace chat (sync + SSE stream)."""

from __future__ import annotations

import asyncio
import json
import queue
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from langchain.agents import create_agent

from agent_server.core.mcp_tools import load_mcp_tools_for_project
from agent_server.core.model_factory import get_llm
from services import procurement_serializers as serializers
from shared.db.repos import projects as project_repo
from shared.logger_global import bind_context, get_logger

log = get_logger(__name__)


def _workspace_agent(system_prompt: str):
    return create_agent(
        model=get_llm(),
        tools=[],
        system_prompt=system_prompt,
        name="workspace_chat",
    )


def _ui_role_to_lc(role: str) -> str:
    if role == "ai":
        return "assistant"
    if role == "user":
        return "user"
    return "user"


def _history_to_lc_messages(history: list | None) -> list[dict]:
    messages: list[dict] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        role = _ui_role_to_lc(str(item.get("role") or "user"))
        messages.append({"role": role, "content": text})
    return messages


def _chunk_text(content: Any) -> str:
    """Extract visible text; skip reasoning-only blocks."""
    if content is None:
        return ""
    if isinstance(content, str):
        stripped = content.strip()
        if stripped.startswith("[{") and '"reasoning"' in stripped:
            return ""
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return ""


def _extract_ai_text(result: dict) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""
    last = messages[-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    return _chunk_text(content).strip()


def _base_system_prompt(project: dict) -> str:
    return (
        "You are Mate, Etex's procurement AI assistant in the project workspace chat. "
        f"Current project: {project['name']} (id={project['id']}, code={project.get('code', '')}). "
        "Answer clearly and helpfully using the MCP project context below when relevant. "
        "Keep replies concise; use short bullet lists when useful."
    )


def _prepare(
    project_id: str,
    owner_id: str,
    message: str,
    history: list | None,
) -> tuple[dict, list, list] | None:
    bind_context(project_id=project_id, workflow="chat.prepare")
    started = time.perf_counter()

    try:
        project_row = project_repo.get_for_owner(project_id, owner_id)
    except project_repo.ProjectNotFoundError:
        log.warning("workspace chat project not found project_id={}", project_id)
        return None
    project = serializers.chat_project_dict(project_row)

    user_text = (message or "").strip()
    if not user_text:
        raise ValueError("message is required")

    tools = load_mcp_tools_for_project(project_id, owner_id)
    lc_messages = _history_to_lc_messages(history)
    lc_messages.append({"role": "user", "content": user_text})

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    log.info(
        "workspace chat prepared history_len={} tool_count={} duration_ms={}",
        len(history or []),
        len(tools),
        duration_ms,
    )
    return project, tools, lc_messages


async def _prefetch_mcp_context(tools: list) -> tuple[list[dict[str, Any]], str]:
    bind_context(workflow="chat.mcp_prefetch")
    started = time.perf_counter()

    events: list[dict[str, Any]] = []
    blobs: list[str] = []
    tool_names = [getattr(t, "name", str(t)) for t in tools]
    events.append(
        {
            "type": "context",
            "label": "MCP tools ready",
            "detail": ", ".join(tool_names) if tool_names else "none",
        }
    )

    for tool in tools:
        name = getattr(tool, "name", "tool")
        tool_started = time.perf_counter()
        try:
            raw = await tool.ainvoke({})
        except Exception as exc:  # noqa: BLE001
            detail = f"{type(exc).__name__}: {str(exc)[:200]}"
            events.append({"type": "context", "label": f"MCP · {name} (failed)", "detail": detail})
            log.warning(
                "mcp tool failed tool={} error={} duration_ms={}",
                name,
                detail,
                round((time.perf_counter() - tool_started) * 1000, 2),
            )
            continue

        if isinstance(raw, (dict, list)):
            text = json.dumps(raw, ensure_ascii=False)
        else:
            text = str(raw)
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    texts = [
                        str(b.get("text") or "")
                        for b in parsed
                        if isinstance(b, dict) and b.get("type") == "text"
                    ]
                    if texts:
                        text = "".join(texts)
                elif isinstance(parsed, dict):
                    text = json.dumps(parsed, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass
        preview = text[:240]
        events.append({"type": "context", "label": f"MCP · {name}", "detail": preview})
        blobs.append(f"### {name}\n{text}")
        log.debug(
            "mcp tool ok tool={} preview_len={} duration_ms={}",
            name,
            len(text),
            round((time.perf_counter() - tool_started) * 1000, 2),
        )

    context_block = "\n\n".join(blobs)
    log.info(
        "mcp prefetch complete tool_count={} duration_ms={}",
        len(tools),
        round((time.perf_counter() - started) * 1000, 2),
    )
    return events, context_block


async def _ainvoke_with_mcp(project: dict, tools: list, lc_messages: list) -> dict:
    _events, context_block = await _prefetch_mcp_context(tools)
    bind_context(workflow="chat.agent_invoke")
    started = time.perf_counter()

    prompt = _base_system_prompt(project)
    if context_block:
        prompt = f"{prompt}\n\n## MCP project context\n{context_block}"

    agent = _workspace_agent(prompt)
    result = await agent.ainvoke({"messages": lc_messages})

    log.info(
        "agent invoke complete duration_ms={}",
        round((time.perf_counter() - started) * 1000, 2),
    )
    return result


def run_workspace_chat(
    project_id: str,
    owner_id: str,
    message: str,
    history: list | None = None,
) -> dict | None:
    """Run create_agent with MCP-prefetch context. Returns AI reply or None."""
    bind_context(project_id=project_id, workflow="chat.sync")
    log.info("workspace chat sync started")

    prepared = _prepare(project_id, owner_id, message, history)
    if prepared is None:
        return None
    project, tools, lc_messages = prepared

    try:
        result = asyncio.run(_ainvoke_with_mcp(project, tools, lc_messages))
    except Exception:
        bind_context(workflow="chat.error")
        log.exception("workspace chat sync failed")
        raise

    text = _extract_ai_text(result) or "I could not generate a reply. Please try again."
    bind_context(workflow="chat.done")
    log.info("workspace chat sync done reply_len={}", len(text))
    return {"role": "ai", "text": text}


async def _astream_events(
    project: dict,
    tools: list,
    lc_messages: list,
) -> AsyncIterator[dict[str, Any]]:
    context_events, context_block = await _prefetch_mcp_context(tools)
    for event in context_events:
        yield event

    bind_context(workflow="chat.stream")
    stream_started = time.perf_counter()
    token_count = 0

    prompt = _base_system_prompt(project)
    if context_block:
        prompt = f"{prompt}\n\n## MCP project context\n{context_block}"

    agent = _workspace_agent(prompt)
    assembled = ""

    async for item in agent.astream(
        {"messages": lc_messages},
        stream_mode="messages",
    ):
        msg = item[0] if isinstance(item, tuple) else item
        piece = _chunk_text(getattr(msg, "content", None))
        if not piece:
            continue
        assembled += piece
        token_count += 1
        yield {"type": "token", "text": piece}

    text = assembled.strip() or "I could not generate a reply. Please try again."
    bind_context(workflow="chat.done")
    log.info(
        "workspace chat stream done token_chunks={} reply_len={} duration_ms={}",
        token_count,
        len(text),
        round((time.perf_counter() - stream_started) * 1000, 2),
    )
    yield {"type": "done", "role": "ai", "text": text}


def iter_workspace_chat_events(
    project_id: str,
    owner_id: str,
    message: str,
    history: list | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield SSE events: MCP context → token stream → done/error."""
    bind_context(project_id=project_id, workflow="chat.stream")
    log.info("workspace chat stream started")

    try:
        prepared = _prepare(project_id, owner_id, message, history)
    except ValueError as exc:
        bind_context(workflow="chat.error")
        log.warning("workspace chat validation error: {}", exc)
        yield {"type": "error", "detail": str(exc)}
        return

    if prepared is None:
        bind_context(workflow="chat.error")
        yield {"type": "error", "detail": "not_found"}
        return

    project, tools, lc_messages = prepared
    out: queue.Queue[dict[str, Any] | None] = queue.Queue()

    async def runner() -> None:
        try:
            async for event in _astream_events(project, tools, lc_messages):
                out.put(event)
        except Exception as exc:  # noqa: BLE001
            bind_context(workflow="chat.error")
            log.exception("workspace chat stream failed: {}", exc)
            out.put(
                {
                    "type": "error",
                    "detail": f"{type(exc).__name__}: {str(exc)[:300]}",
                }
            )
        finally:
            out.put(None)

    thread = threading.Thread(target=lambda: asyncio.run(runner()), daemon=True)
    thread.start()

    while True:
        item = out.get()
        if item is None:
            break
        yield item

    thread.join(timeout=1)


def sse_format(event: dict[str, Any]) -> str:
    """Encode one SSE frame (event name = type, data = JSON)."""
    event_type = event.get("type") or "message"
    payload = {k: v for k, v in event.items() if k != "type"}
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
