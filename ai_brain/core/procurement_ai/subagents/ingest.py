"""Upload → per-file parse fan-out (LangGraph Send). Already-parsed files are recorded, not re-read."""

from __future__ import annotations

from typing import Any, Optional

import mlflow
from langchain_core.runnables import RunnableConfig
from mlflow.entities import SpanType

from ai_brain.core.procurement_ai.capabilities import project_id_from_state
from ai_brain.core.procurement_ai.project_context import load_artifacts


def _procurement(state: dict[str, Any]) -> dict[str, Any]:
    return dict(state.get("procurement") or {})


@mlflow.trace(name="procura_list_artifacts", span_type=SpanType.TOOL)
def list_artifacts(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    project_id = project_id_from_state(state)
    artifacts = load_artifacts(project_id) if project_id else []
    ids = [str(getattr(item, "id", "") or "") for item in artifacts]
    ids = [item for item in ids if item]
    return {
        "procurement": {
            "artifact_ids": ids,
            "file_count": len(ids),
            "pipeline_stage": "parse",
        }
    }


def fanout_parse(state: dict[str, Any]) -> list:
    """Map: one Send per uploaded artifact. Empty drop still joins at assemble."""
    try:
        from langgraph.types import Send
    except ImportError:  # tests / environments without LangGraph

        class Send:  # type: ignore[no-redef]
            def __init__(self, node: str, arg: dict[str, Any]):
                self.node = node
                self.arg = arg

    base = {
        "request": state.get("request") or "",
        "project_id": state.get("project_id") or project_id_from_state(state),
        "capability": state.get("capability") or "",
    }
    ids = list(_procurement(state).get("artifact_ids") or [])
    if not ids:
        return [Send("assemble_parse", {**base, "procurement": _procurement(state)})]
    return [
        Send(
            "parse_artifact",
            {
                **base,
                "procurement": {**_procurement(state), "artifact_id": artifact_id},
            },
        )
        for artifact_id in ids
    ]


@mlflow.trace(name="procura_parse_artifact", span_type=SpanType.TOOL)
def parse_artifact(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    artifact_id = str(_procurement(state).get("artifact_id") or "")
    status = "skipped"
    if artifact_id:
        try:
            from shared.db.connection import session_scope
            from shared.db.models import Artifact

            with session_scope() as session:
                artifact = session.get(Artifact, artifact_id)
                if artifact is None:
                    status = "missing"
                    artifact = None
                else:
                    status = artifact.parse_status or ""
                    session.expunge(artifact)
            if artifact is None:
                status = status or "missing"
            elif status in {"ok", "skipped", "error"}:
                pass
            else:
                try:
                    from services.artifact_parse import parse_and_store
                except ImportError:
                    import sys
                    from pathlib import Path

                    backend = Path(__file__).resolve().parents[4] / "backend"
                    if str(backend) not in sys.path:
                        sys.path.insert(0, str(backend))
                    from services.artifact_parse import parse_and_store

                status = parse_and_store(artifact).parse_status
        except Exception as exc:  # noqa: BLE001
            status = f"error:{exc.__class__.__name__}"
    return {
        "procurement": {
            "parse_results": [{"artifact_id": artifact_id, "status": status}],
        }
    }


@mlflow.trace(name="procura_assemble_parse", span_type=SpanType.CHAIN)
def assemble_parse(
    state: dict[str, Any],
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    results = list(_procurement(state).get("parse_results") or [])
    ok = sum(1 for row in results if row.get("status") == "ok")
    return {
        "procurement": {
            "parsed_ok": ok,
            "parse_count": len(results),
            "pipeline_stage": "kb_kg",
        }
    }
