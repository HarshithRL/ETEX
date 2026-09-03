"""Nexus MLflow AgentServer wrapping the Procura AI graph."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Running as a script (``python ai_brain/brain_server.py``) puts ai_brain/ on
# sys.path instead of the repo root, so the package is not importable yet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_brain.server.bootstrap import ensure_repo_root

ensure_repo_root()

from shared.logger_global import get_logger, setup_logging

setup_logging(service="ai_brain")

from ai_brain.server.tracing import configure_tracing

configure_tracing()

from ai_brain.server import agent as _agent_handlers  # noqa: F401  # registers @invoke/@stream
from ai_brain.server.middleware import install_middleware
from ai_brain.server.routes import register_routes
from ai_brain.server.runtime import runtime
from fastapi import FastAPI
from mlflow.genai.agent_server import AgentServer
from mlflow.genai.agent_server.validator import ResponsesAgentValidator
import mlflow

log = get_logger(__name__, service="ai_brain")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8004


@asynccontextmanager
async def lifespan(_app: Any):
    await runtime.start()
    try:
        yield
    finally:
        await runtime.stop()
        try:
            mlflow.flush_trace_async_logging()
        except Exception:
            pass


class NexusAgentServer(AgentServer):
    """AgentServer on a FastAPI app we construct (Starlette 1.6 dropped on_startup)."""

    def __init__(self) -> None:
        self.agent_type = "ResponsesAgent"
        self.validator = ResponsesAgentValidator()
        self.app = FastAPI(
            title="AI Brain Agent Server",
            description="MLflow AgentServer wrapping the Nexus LangGraph",
            lifespan=lifespan,
        )
        self.app.max_body_size = None
        self._setup_routes()


agent_server = NexusAgentServer()
app = agent_server.app
install_middleware(app)
register_routes(app)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Brain MLflow AgentServer")
    parser.add_argument("--host", default=os.getenv("BRAIN_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("BRAIN_PORT", str(DEFAULT_PORT))))
    args = parser.parse_args()
    import uvicorn

    log.info("starting ai_brain AgentServer on {}:{}", args.host, args.port)
    uvicorn.run(
        "ai_brain.brain_server:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
