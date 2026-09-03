"""Project insights, pack status, and pack-run routes Flask already proxies to."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from mlflow.types.responses import ResponsesAgentRequest

from ai_brain.core.procurement_ai.capabilities import PACK_CAPABILITIES, normalize_capability
from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.packs import store as pack_store
from ai_brain.core.procurement_ai.project_context import load_context, load_project
from ai_brain.server.agent import non_streaming
from ai_brain.server.request import normalize_thread_id
from ai_brain.server.schemas import ProjectRunRequest


def register_project_routes(app: FastAPI) -> None:
    @app.get("/v1/projects/{project_id}/insights")
    def project_insights(project_id: str) -> dict[str, Any]:
        project, artifacts, chunks = load_context(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        return build_insight_payload(project, artifacts, chunks)

    @app.get("/v1/projects/{project_id}/packs")
    def project_packs(project_id: str) -> dict[str, Any]:
        if load_project(project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")
        return pack_store.read_status(project_id)

    @app.post("/v1/projects/{project_id}/runs")
    async def project_run(project_id: str, body: ProjectRunRequest):
        from ai_brain.server.routes import _thread_state_or_404, _values_to_invoke_response
        from ai_brain.server.streaming import _interrupts_from_state

        capability = normalize_capability(body.capability)
        if capability not in PACK_CAPABILITIES:
            raise HTTPException(
                status_code=400,
                detail="capability must be compare_xlsx or steerco_ppt",
            )
        if load_project(project_id) is None:
            raise HTTPException(status_code=404, detail="project not found")

        text = (body.message or capability).strip()
        thread_id = normalize_thread_id(body.thread_id or f"{project_id}:{capability}")
        request = ResponsesAgentRequest(
            input=[{"role": "user", "content": text, "type": "message"}],
            custom_inputs={
                "request": text,
                "procurement": {
                    "capability": capability,
                    "project_id": project_id,
                },
                "thread_id": thread_id,
            },
        )
        result = await non_streaming(request)
        custom = result.custom_outputs or {}
        _, _, state, values = await _thread_state_or_404(thread_id)
        return _values_to_invoke_response(
            values if isinstance(values, dict) else {},
            request_text=text,
            thread_id=str(custom.get("thread_id") or thread_id),
            interrupts=list(custom.get("interrupts") or _interrupts_from_state(state)),
        )
