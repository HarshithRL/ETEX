"""Comparison-facts overlay. Deep Agent (or a chunk scan) fills this; Excel only reads it."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_brain.core.procurement_ai.pipeline import read_json, write_json

FACTS_FILE = "comparison_facts.json"
MISSING = "missing"


def load_facts(project_id: str) -> dict[str, Any] | None:
    return read_json(project_id, FACTS_FILE)


def save_facts(project_id: str, payload: dict[str, Any]) -> str:
    cleaned = normalize_facts(payload)
    return write_json(project_id, FACTS_FILE, cleaned)


def parse_facts_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("facts payload must be an object")
    return normalize_facts(data)


def normalize_facts(payload: dict[str, Any]) -> dict[str, Any]:
    vendors = []
    for row in payload.get("vendors") or []:
        if not isinstance(row, dict):
            continue
        vendors.append(
            {
                "name": str(row.get("name") or "").strip(),
                "headline": str(row.get("headline") or "").strip(),
                "external_cost": _missing_or_value(row.get("external_cost")),
                "internal_days": _missing_or_value(row.get("internal_days")),
                "day_rate": _missing_or_value(row.get("day_rate")),
                "currency": str(row.get("currency") or "EUR"),
                "evidence": list(row.get("evidence") or []),
            }
        )
    requirements = []
    for row in payload.get("requirements") or []:
        if not isinstance(row, dict):
            continue
        requirements.append(
            {
                "id": str(row.get("id") or "").strip(),
                "label": str(row.get("label") or "").strip(),
                "severity": str(row.get("severity") or "blocking"),
                "vendor_status": dict(row.get("vendor_status") or {}),
                "evidence": list(row.get("evidence") or []),
            }
        )
    red_flags = []
    for row in payload.get("red_flags") or []:
        if isinstance(row, dict):
            red_flags.append(row)
        elif row:
            red_flags.append({"severity": "blocking", "item": str(row)})
    return {
        "process_type": str(payload.get("process_type") or ""),
        "vendors": vendors,
        "requirements": requirements,
        "red_flags": red_flags,
    }


def overlay_insights(insights: dict[str, Any], facts: dict[str, Any] | None) -> dict[str, Any]:
    """Non-missing extracted fields win. Filename cards remain if extract is silent."""
    if not facts:
        return insights
    out = dict(insights)
    by_name = {str(v.get("name") or "").lower(): v for v in facts.get("vendors") or []}
    vendors = []
    for vendor in out.get("vendors") or []:
        extra = by_name.get(str(vendor.get("name") or "").lower()) or {}
        merged = dict(vendor)
        if extra.get("headline"):
            merged["headline"] = extra["headline"]
        merged["external_cost"] = extra.get("external_cost") or MISSING
        merged["internal_days"] = extra.get("internal_days") or MISSING
        merged["day_rate"] = extra.get("day_rate") or MISSING
        if extra.get("evidence"):
            merged["evidence"] = extra["evidence"]
        vendors.append(merged)
    out["vendors"] = vendors
    if facts.get("requirements"):
        req = dict(out.get("requirements") or {})
        req["extracted"] = facts["requirements"]
        out["requirements"] = req
    if facts.get("red_flags"):
        decision = dict(out.get("decision") or {})
        existing = list(decision.get("blockers") or [])
        for flag in facts["red_flags"]:
            item = flag.get("item") if isinstance(flag, dict) else str(flag)
            if item and item not in existing:
                existing.append(item)
        decision["blockers"] = existing
        out["decision"] = decision
    out["comparison_facts"] = True
    return out


def scan_chunks_for_facts(insights: dict[str, Any], chunks: list[Any]) -> dict[str, Any]:
    """Deterministic fallback when Deep Agent has not saved facts yet. Cite or missing."""
    vendors = []
    for vendor in insights.get("vendors") or []:
        name = str(vendor.get("name") or "")
        blob, hit = _chunks_for_vendor(name, chunks)
        days = _first_match(r"(\d+(?:[.,]\d+)?)\s*(?:man[\s-]?days?|mandays?|person[\s-]?days?)", blob)
        rate = _first_match(r"(?:€|eur|euro)\s*([0-9][0-9.,]*)", blob) or _first_match(
            r"([0-9][0-9.,]*)\s*(?:€|eur)/?\s*(?:day|d)\b", blob
        )
        evidence = []
        if hit is not None:
            evidence.append(
                {
                    "artifact": getattr(hit, "artifact_id", ""),
                    "locator": f"chunk {getattr(hit, 'ordinal', 0)}",
                    "quote": (getattr(hit, "text", "") or "")[:180],
                }
            )
        vendors.append(
            {
                "name": name,
                "headline": vendor.get("headline") or "",
                "external_cost": MISSING,
                "internal_days": days or MISSING,
                "day_rate": rate or MISSING,
                "currency": "EUR",
                "evidence": evidence or vendor.get("evidence") or [],
            }
        )
    return normalize_facts(
        {
            "process_type": insights.get("process_type") or "",
            "vendors": vendors,
            "requirements": [
                {
                    "id": item.get("checklist_key") or item.get("id"),
                    "label": item.get("label"),
                    "severity": item.get("severity") or "blocking",
                    "vendor_status": {},
                    "evidence": [],
                }
                for item in (insights.get("requirements") or {}).get("items") or []
            ],
            "red_flags": [{"item": b} for b in (insights.get("decision") or {}).get("blockers") or []],
        }
    )


def _missing_or_value(value: Any) -> Any:
    if value is None or value == "" or value == MISSING:
        return MISSING
    return value


def _chunks_for_vendor(name: str, chunks: list[Any]) -> tuple[str, Any]:
    needle = name.lower()
    texts = []
    first = None
    for chunk in chunks:
        text = getattr(chunk, "text", "") or ""
        if needle and needle in text.lower():
            texts.append(text)
            if first is None:
                first = chunk
    if not texts:
        for chunk in chunks:
            texts.append(getattr(chunk, "text", "") or "")
            if first is None:
                first = chunk
    return "\n".join(texts), first


def _first_match(pattern: str, blob: str) -> str | None:
    match = re.search(pattern, blob or "", flags=re.IGNORECASE)
    return match.group(1) if match else None
