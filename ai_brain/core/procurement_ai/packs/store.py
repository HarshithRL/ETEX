"""On-disk pack status for comparison Excel and SteerCo PPT."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KINDS = ("xlsx", "ppt")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def projects_data_root() -> Path:
    override = os.getenv("MATE_PROJECTS_DATA_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "data" / "projects"


def project_root(project_id: str) -> Path:
    return projects_data_root() / project_id


def packs_dir(project_id: str) -> Path:
    path = project_root(project_id) / "packs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def status_path(project_id: str) -> Path:
    return packs_dir(project_id) / "status.json"


def read_status(project_id: str) -> dict[str, Any]:
    path = status_path(project_id)
    if not path.exists():
        return {
            "xlsx": {"status": "idle", "href": None, "thread_id": None, "filename": None},
            "ppt": {"status": "idle", "href": None, "thread_id": None, "filename": None},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = {}
    out = {}
    for kind in KINDS:
        row = data.get(kind) if isinstance(data.get(kind), dict) else {}
        out[kind] = {
            "status": row.get("status") or "idle",
            "href": row.get("href"),
            "thread_id": row.get("thread_id"),
            "filename": row.get("filename"),
            "error": row.get("error"),
            "updated_at": row.get("updated_at"),
        }
    return out


def pack_status(project_id: str) -> dict[str, Any]:
    return read_status(project_id)


def write_status(project_id: str, kind: str, **fields: Any) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"unknown pack kind: {kind}")
    current = read_status(project_id)
    current[kind] = {**current[kind], **fields, "updated_at": utc_now_iso()}
    status_path(project_id).write_text(
        json.dumps(current, indent=2),
        encoding="utf-8",
    )
    return current


def pack_file(project_id: str, filename: str) -> Path:
    return packs_dir(project_id) / filename


def flask_href(project_id: str, kind: str) -> str:
    return f"/api/procurement/projects/{project_id}/packs/{kind}/download"
