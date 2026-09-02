"""Parse and strip the Project Initiator JSON draft trailer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from agent_server.core.state import ProjectDraft

DraftReason = Literal["", "parse_failed", "empty_name", "missing_workflow"]


@dataclass(frozen=True)
class DraftValidation:
    ok: bool
    reason: DraftReason
    draft: ProjectDraft | None

_DRAFT_FENCE = re.compile(
    r"```json\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)

DRAFT_FENCE_START = "```json"

_WORKFLOWS = ("Sourcing", "Vendor Comparison", "Contract Negotiation")
_PROCESSES = ("Indirect", "Direct")


def split_visible_and_draft(text: str) -> tuple[str, ProjectDraft | None]:
    """Return (visible reply, parsed draft or None)."""
    if not text:
        return "", None
    match = _DRAFT_FENCE.search(text)
    if not match:
        visible = text
        fence_at = text.find(DRAFT_FENCE_START)
        if fence_at != -1:
            visible = text[:fence_at]
        return visible.strip(), None
    visible = (text[: match.start()] + text[match.end() :]).strip()
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        return visible, None
    if not isinstance(raw, dict):
        return visible, None
    return visible, _coerce_draft(raw)


def _match_option(value: Any, options: tuple[str, ...], aliases: tuple[tuple[str, str], ...] = ()) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    lower = raw.lower()
    for option in options:
        if option.lower() == lower:
            return option
    for needle, option in aliases:
        if needle in lower:
            return option
    return ""


def _clean_requirements(raw: Any) -> list[str | dict[str, str]]:
    if isinstance(raw, str):
        items = [raw] if raw.strip() else []
    elif isinstance(raw, list):
        items = raw
    else:
        items = []

    cleaned: list[str | dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item.strip()
            if text:
                cleaned.append(text)
            continue
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("requirement") or "").strip()
        ref = str(item.get("ref") or "").strip()
        weight = str(item.get("weight") or "").strip()
        if not text and not ref:
            continue
        cleaned.append({"ref": ref, "text": text, "weight": weight})
    return cleaned


def _text(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _coerce_draft(raw: dict[str, Any]) -> ProjectDraft:
    workflow = _match_option(
        raw.get("workflowEntryPoint") or raw.get("workflowPhase") or raw.get("workflow"),
        _WORKFLOWS,
        (
            ("compar", "Vendor Comparison"),
            ("negoti", "Contract Negotiation"),
            ("contract", "Contract Negotiation"),
            ("sourc", "Sourcing"),
        ),
    )
    process = _match_option(raw.get("businessProcess"), _PROCESSES)
    description = _text(raw, "description", "brief")
    draft: ProjectDraft = {
        "name": _text(raw, "name"),
        "workflowEntryPoint": workflow,
        "businessProcess": process,
        "requester": _text(raw, "requester"),
        "dept": _text(raw, "dept"),
        "targetSpend": _text(raw, "targetSpend"),
        "category": _text(raw, "category"),
        "awardHorizon": _text(raw, "awardHorizon"),
        "region": _text(raw, "region"),
        "description": description,
        "brief": description,
        "requirements": _clean_requirements(raw.get("requirements")),
    }
    return draft


def draft_has_meaningful_fields(draft: ProjectDraft | None) -> bool:
    if not draft:
        return False
    for key, value in draft.items():
        if value in ("", [], None):
            continue
        return True
    return False


def validate_draft(draft: ProjectDraft | None) -> DraftValidation:
    if draft is None:
        return DraftValidation(ok=False, reason="parse_failed", draft=None)
    name = str(draft.get("name") or "").strip()
    if not name:
        return DraftValidation(ok=False, reason="empty_name", draft=draft)
    workflow = str(draft.get("workflowEntryPoint") or "").strip()
    if not workflow:
        return DraftValidation(ok=False, reason="missing_workflow", draft=draft)
    return DraftValidation(ok=True, reason="", draft=draft)


def question_for_reason(reason: DraftReason) -> str:
    if reason == "empty_name":
        return "What should we call this project?"
    if reason == "missing_workflow":
        return (
            "Which workflow phase are you in — Sourcing, Vendor Comparison, "
            "or Contract Negotiation?"
        )
    return ""
