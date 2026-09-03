"""Project knowledge base for workspace chat — parsed chunks, retrieved into create_agent."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.project_context import load_context

HIT_LIMIT = 8
HIT_CHAR_LIMIT = 900
BLOCK_CHAR_LIMIT = 12_000
_TOKEN = re.compile(r"[a-z0-9]{3,}")
_STOP = frozenset(
    {
        "the",
        "and",
        "for",
        "this",
        "that",
        "what",
        "who",
        "how",
        "are",
        "was",
        "with",
        "from",
        "about",
        "project",
        "please",
        "tell",
        "give",
        "ask",
    }
)


def knowledge_prompt_block(project_id: str, query: str) -> str:
    """Return a system-prompt block of project facts + ranked excerpts, or empty."""
    pid = (project_id or "").strip()
    if not pid:
        return ""
    project, artifacts, chunks = load_context(pid)
    if project is None:
        return (
            "## Project knowledge base\n"
            "No project is attached to this thread. Do not invent files, prices, or scores."
        )
    insights = build_insight_payload(project, artifacts, chunks)
    hits = search_chunks(query, artifacts, chunks)
    parts = ["## Project knowledge base", _header(insights)]
    if not chunks:
        parts.append(
            "No parsed excerpts yet. Answer from the header only; say missing for facts not in files."
        )
        return "\n".join(parts)
    if hits:
        parts.append("### Retrieved excerpts")
        parts.append("Cite file + locator. No citation = opinion. Do not invent numbers.")
        used = 0
        for hit in hits:
            block = _format_hit(hit)
            if used + len(block) > BLOCK_CHAR_LIMIT:
                break
            parts.append(block)
            used += len(block)
    else:
        parts.append("No excerpt matched this question. Say missing rather than guessing.")
    return "\n".join(parts)


def search_chunks(
    query: str,
    artifacts: list[Any],
    chunks: list[Any],
    *,
    limit: int = HIT_LIMIT,
) -> list[dict[str, Any]]:
    names = {
        getattr(artifact, "id", ""): getattr(artifact, "original_name", "") or "document"
        for artifact in artifacts or []
    }
    terms = _query_tokens(query)
    scored: list[tuple[int, int, Any]] = []
    for ordinal, chunk in enumerate(chunks or []):
        text = (getattr(chunk, "text", "") or "").strip()
        if not text:
            continue
        filename = names.get(getattr(chunk, "artifact_id", ""), "document")
        score = _score(terms, text, filename, _heading(chunk))
        scored.append((score, ordinal, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected = [item for item in scored if item[0] > 0][:limit]
    if not selected:
        selected = scored[: min(3, len(scored))]
    hits: list[dict[str, Any]] = []
    for score, _ordinal, chunk in selected:
        filename = names.get(getattr(chunk, "artifact_id", ""), "document")
        text = (getattr(chunk, "text", "") or "").strip()
        hits.append(
            {
                "file": filename,
                "locator": chunk_locator(chunk),
                "heading": _heading(chunk),
                "text": text[:HIT_CHAR_LIMIT],
                "score": score,
            }
        )
    return hits


def chunk_locator(chunk: Any) -> str:
    raw = getattr(chunk, "location_json", None)
    if not raw:
        raw = getattr(chunk, "location", None)
    if not raw:
        return f"chunk {getattr(chunk, 'ordinal', 0)}"
    try:
        loc = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return f"chunk {getattr(chunk, 'ordinal', 0)}"
    if loc.get("page") is not None:
        return f"p.{loc['page']}"
    if loc.get("slide") is not None:
        return f"slide {loc['slide']}"
    if loc.get("sheet"):
        return str(loc["sheet"])
    return loc.get("locator") or f"chunk {getattr(chunk, 'ordinal', 0)}"


def _header(insights: dict[str, Any]) -> str:
    vendors = ", ".join(
        str(vendor.get("name") or "").strip()
        for vendor in insights.get("vendors") or []
        if vendor.get("name")
    )
    return (
        f"Project: {insights.get('project_code') or ''} {insights.get('project_name') or ''}\n"
        f"Process: {insights.get('process_type') or 'unset'} · KB {insights.get('kb_status') or 'empty'}\n"
        f"Files: {insights.get('file_count') or 0} uploaded, {insights.get('parsed_ok') or 0} parsed\n"
        f"Vendors: {vendors or 'none yet'}"
    )


def _format_hit(hit: dict[str, Any]) -> str:
    heading = hit.get("heading") or ""
    title = f"[{hit.get('file') or 'document'} · {hit.get('locator') or 'excerpt'}]"
    if heading:
        title = f"{title} {heading}"
    return f"{title}\n{hit.get('text') or ''}"


def _heading(chunk: Any) -> str:
    raw = getattr(chunk, "heading_path_json", None)
    if not raw:
        path = getattr(chunk, "heading_path", None)
        if isinstance(path, (list, tuple)):
            return " > ".join(str(part) for part in path if part)
        return ""
    try:
        path = json.loads(raw) if isinstance(raw, str) else list(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ""
    return " > ".join(str(part) for part in path if part)


def _query_tokens(query: str) -> set[str]:
    return {token for token in _TOKEN.findall((query or "").lower()) if token not in _STOP}


def _score(terms: set[str], text: str, filename: str, heading: str) -> int:
    if not terms:
        return 1
    hay = f"{filename} {heading} {text}".lower()
    hay_tokens = set(_TOKEN.findall(hay))
    overlap = terms & hay_tokens
    if not overlap:
        return 0
    return len(overlap) * 10 + sum(hay.count(token) for token in overlap)
