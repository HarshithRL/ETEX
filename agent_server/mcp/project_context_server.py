"""MCP server: project workspace context tools for Mate create_agent."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
for path in (_REPO_ROOT, _BACKEND):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mcp.server.fastmcp import FastMCP

from services.procurement_serializers import workspace_payload
from shared.db.repos import artifacts as artifact_repo
from shared.db.repos import projects as project_repo

mcp = FastMCP("mate-project-context")


def _project_id() -> str:
    return (os.environ.get("MATE_PROJECT_ID") or "").strip()


def _owner_id() -> str:
    return (os.environ.get("MATE_OWNER_ID") or "").strip()


@mcp.tool()
def get_project_context() -> str:
    """Return metadata for the current procurement project (name, code, status, owner, dates)."""
    project_id = _project_id()
    owner_id = _owner_id()
    if not project_id or not owner_id:
        return json.dumps({"error": "project_not_found", "project_id": project_id})
    try:
        project = project_repo.get_for_owner(project_id, owner_id)
    except project_repo.ProjectNotFoundError:
        return json.dumps({"error": "project_not_found", "project_id": project_id})
    return json.dumps(
        {
            "id": project.id,
            "name": project.name,
            "code": project.code,
            "status": project.status,
            "owner": project_repo.project_to_dict(project)["owner"],
            "created": project_repo.project_to_dict(project)["created"],
            "deadline": project.deadline,
            "progress": project.progress,
        }
    )


@mcp.tool()
def list_workspace_files() -> str:
    """List Input / AI Generated / Artifact file names for the current project workspace."""
    project_id = _project_id()
    owner_id = _owner_id()
    if not project_id or not owner_id:
        return json.dumps({"error": "project_not_found", "project_id": project_id})
    try:
        project = project_repo.get_for_owner(project_id, owner_id)
        artifacts = artifact_repo.list_for_project(project_id, owner_id)
    except project_repo.ProjectNotFoundError:
        return json.dumps({"error": "project_not_found", "project_id": project_id})
    workspace = workspace_payload(project, artifacts, user_initial="")
    files = workspace.get("files") or {}
    return json.dumps(
        {
            "projectName": workspace.get("projectName"),
            "inputs": files.get("inputs"),
            "generated": files.get("generated"),
            "artifacts": files.get("artifacts"),
            "inputsCount": files.get("inputsCount"),
        }
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
