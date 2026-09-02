"""FastAPI wrapper around the Mate agent graph (new-project intake SSE)."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) in sys.path:
    sys.path.remove(str(_SCRIPT_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from shared.logger_global import bind_context, get_logger, setup_logging

setup_logging(service="agent_server")

from agent_server.core.streaming import iter_sse_events
from agent_server.graph import graph

log = get_logger(__name__, service="agent_server")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

app = FastAPI(title="Mate Agent Server", version="0.1.0")
# Credentialed fetch cannot use wildcard headers; Starlette rejects that preflight with 400.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


class StreamRequest(BaseModel):
    message: str
    thread_id: str = ""
    route: str = "new_project"
    history: list[dict[str, Any]] = Field(default_factory=list)


def _sse_frame(event: dict[str, Any]) -> dict[str, str]:
    event_type = event.get("type") or "message"
    payload = {k: v for k, v in event.items() if k != "type"}
    return {"event": event_type, "data": json.dumps(payload, ensure_ascii=False)}


async def _stream_graph(body: StreamRequest) -> AsyncIterator[dict[str, str]]:
    user_text = (body.message or "").strip()
    if not user_text:
        yield _sse_frame({"type": "error", "detail": "message is required"})
        return

    thread_id = (body.thread_id or "").strip() or str(uuid.uuid4())
    route = (body.route or "new_project").strip() or "new_project"
    bind_context(workflow="agent.stream", request_id=thread_id)
    log.info("agent stream started route={} thread_id={}", route, thread_id)

    payload: dict[str, Any] = {
        "messages": [{"role": "user", "content": user_text}],
        "route": route,
        "thread_id": thread_id,
    }

    try:
        stream = graph.astream(
            payload,
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=["messages", "updates"],
            subgraphs=True,
            version="v2",
        )
        async for event in iter_sse_events(stream):
            yield _sse_frame(event)
    except Exception as exc:  # noqa: BLE001
        log.exception("agent stream failed")
        yield _sse_frame(
            {
                "type": "error",
                "detail": f"{type(exc).__name__}: {str(exc)[:300]}",
            }
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agent_server"}


@app.post("/agent/stream")
async def agent_stream(body: StreamRequest) -> EventSourceResponse:
    if not (body.message or "").strip():
        raise HTTPException(status_code=400, detail="message is required")
    return EventSourceResponse(_stream_graph(body), sep="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mate agent FastAPI server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    import uvicorn

    log.info("starting agent FastAPI on {}:{}", args.host, args.port)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
