"""Deep Agent tools. Read chunks / insights, persist facts. No LLM import here."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from ai_brain.core.procurement_ai.extraction import parse_facts_json, save_facts
from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.pipeline import persist_kb, read_json
from ai_brain.core.procurement_ai.project_context import load_context


def _chunks_payload(project_id: str, query: str = "", limit: int = 40) -> list[dict[str, Any]]:
    _project, artifacts, chunks = load_context(project_id)
    names = {getattr(a, "id", ""): getattr(a, "original_name", "") for a in artifacts}
    needle = (query or "").strip().lower()
    rows = []
    for chunk in chunks:
        text = (getattr(chunk, "text", "") or "").strip()
        if not text:
            continue
        if needle and needle not in text.lower() and needle not in (names.get(getattr(chunk, "artifact_id", "")) or "").lower():
            continue
        rows.append(
            {
                "artifact": names.get(getattr(chunk, "artifact_id", ""), getattr(chunk, "artifact_id", "")),
                "locator": f"chunk {getattr(chunk, 'ordinal', 0)}",
                "quote": text[:500],
            }
        )
        if len(rows) >= limit:
            break
    return rows


@tool
def list_project_chunks(project_id: str, query: str = "") -> str:
    """Return cited parsed chunks for this project. Filter with query (vendor name or keyword). Never invent text."""
    if not project_id:
        return json.dumps({"error": "project_id required"})
    rows = _chunks_payload(project_id, query=query)
    return json.dumps({"count": len(rows), "chunks": rows}, ensure_ascii=False)


@tool
def load_project_insights(project_id: str) -> str:
    """Filename-level insight cards already built for this project (process type, vendors, gaps)."""
    if not project_id:
        return json.dumps({"error": "project_id required"})
    project, artifacts, chunks = load_context(project_id)
    if project is None:
        return json.dumps({"error": "project not found"})
    payload = build_insight_payload(project, artifacts, chunks)
    payload.pop("pipeline", None)
    return json.dumps(payload, ensure_ascii=False, default=str)


@tool
def save_comparison_facts(project_id: str, facts_json: str) -> str:
    """Persist comparison facts JSON. Empty commercials must be the string 'missing', never 0."""
    if not project_id:
        return json.dumps({"error": "project_id required"})
    try:
        facts = parse_facts_json(facts_json)
        path = save_facts(project_id, facts)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})
    return json.dumps(
        {
            "saved": path,
            "vendors": len(facts.get("vendors") or []),
            "requirements": len(facts.get("requirements") or []),
            "red_flags": len(facts.get("red_flags") or []),
        }
    )


@tool
def save_knowledge_base(project_id: str) -> str:
    """Rebuild and persist the knowledge base from current files + any saved facts."""
    if not project_id:
        return json.dumps({"error": "project_id required"})
    project, artifacts, chunks = load_context(project_id)
    if project is None:
        return json.dumps({"error": "project not found"})
    payload = persist_kb(project_id, project, artifacts, chunks)
    return json.dumps({"status": payload.get("status"), "path": payload.get("path"), "missing": payload.get("missing")})


@tool
def load_saved_facts(project_id: str) -> str:
    """Load comparison facts already saved for this project, if any."""
    data = read_json(project_id, "comparison_facts.json") if project_id else None
    return json.dumps(data or {"status": "empty"})


def deep_agent_tools() -> list:
    return [
        list_project_chunks,
        load_project_insights,
        save_comparison_facts,
        save_knowledge_base,
        load_saved_facts,
    ]
