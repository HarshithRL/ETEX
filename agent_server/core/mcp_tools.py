"""Load LangChain tools from MCP servers (langchain-mcp-adapters)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from shared.logger_global import bind_context, get_logger

log = get_logger(__name__, service="agent_server")

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_CONTEXT_SERVER = _REPO_ROOT / "mcp" / "project_context_server.py"


def _default_connections(project_id: str, owner_id: str) -> dict:
    """Stdio MCP for Mate project context; optional extra servers via env JSON later."""
    env = {
        **os.environ,
        "MATE_PROJECT_ID": project_id,
        "MATE_OWNER_ID": owner_id,
        "PYTHONPATH": os.pathsep.join(
            [
                str(_REPO_ROOT.parent),
                str(_REPO_ROOT.parent / "backend"),
                os.environ.get("PYTHONPATH", ""),
            ]
        ),
    }
    return {
        "project_context": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(_PROJECT_CONTEXT_SERVER)],
            "env": env,
        }
    }


async def _load_tools_async(project_id: str, owner_id: str) -> list[BaseTool]:
    bind_context(project_id=project_id, workflow="mcp.load_tools")
    log.debug("loading mcp tools project_id={}", project_id)
    client = MultiServerMCPClient(_default_connections(project_id, owner_id))
    tools = await client.get_tools()
    log.info("mcp tools loaded project_id={} count={}", project_id, len(tools))
    return tools


def load_mcp_tools_for_project(project_id: str, owner_id: str = "") -> list[BaseTool]:
    """Sync wrapper: load MCP tools scoped to ``project_id``."""
    try:
        return asyncio.run(_load_tools_async(project_id, owner_id))
    except RuntimeError:
        log.debug("mcp load using new event loop project_id={}", project_id)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_load_tools_async(project_id, owner_id))
        finally:
            loop.close()
