from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProcurementFlags(BaseModel):
    mainagent: bool = False
    deepagent: bool = False


class ProcurementResult(ProcurementFlags):
    main_agent: str = ""
    deep_agent: str = ""


class InvokeRequest(BaseModel):
    request: str
    procurement: ProcurementFlags = Field(default_factory=ProcurementFlags)
    thread_id: str = ""
    resume: Any | None = None
    checkpoint_id: str | None = None


class InvokeResponse(BaseModel):
    request: str = ""
    route: str = ""
    thread_id: str = ""
    interrupted: bool = False
    interrupts: list[Any] = Field(default_factory=list)
    procurement: ProcurementResult = Field(default_factory=ProcurementResult)


class ResumeRequest(BaseModel):
    resume: Any
    checkpoint_id: str | None = None
