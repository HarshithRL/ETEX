"""LangGraph checkpointer factory (memory / sqlite / postgres)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from shared.logger_global import get_logger

log = get_logger(__name__, service="ai_brain")


@dataclass
class CheckpointHandle:
    saver: Any
    close: Callable[[], Awaitable[None]] | None = None


async def open_checkpointer() -> CheckpointHandle:
    backend = os.getenv("BRAIN_CHECKPOINT_BACKEND", "sqlite").strip().lower()
    if backend in {"memory", "inmemory", "in-memory"}:
        log.info("checkpointer backend=memory")
        return CheckpointHandle(InMemorySaver())

    if backend == "sqlite":
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        import aiosqlite

        path = os.getenv(
            "BRAIN_CHECKPOINT_SQLITE_PATH",
            str(Path(__file__).resolve().parents[1] / ".checkpoints" / "nexus.sqlite"),
        )
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(path)
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        log.info("checkpointer backend=sqlite path={}", path)

        async def close() -> None:
            await conn.close()

        return CheckpointHandle(saver, close)

    if backend == "postgres":
        uri = (
            os.getenv("BRAIN_CHECKPOINT_POSTGRES_URI", "").strip()
            or os.getenv("DATABASE_URL", "").strip()
        )
        if not uri:
            raise RuntimeError(
                "BRAIN_CHECKPOINT_BACKEND=postgres requires BRAIN_CHECKPOINT_POSTGRES_URI"
            )
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        except ImportError as exc:
            raise RuntimeError(
                "Install langgraph-checkpoint-postgres for postgres checkpointer"
            ) from exc

        cm = AsyncPostgresSaver.from_conn_string(uri)
        saver = await cm.__aenter__()
        await saver.setup()
        log.info("checkpointer backend=postgres")

        async def close() -> None:
            await cm.__aexit__(None, None, None)

        return CheckpointHandle(saver, close)

    raise RuntimeError(f"Unknown BRAIN_CHECKPOINT_BACKEND: {backend}")
