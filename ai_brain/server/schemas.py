from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProcurementFlags(BaseModel):
    mainagent: bool = False
    deepagent: bool = False
    capability: str = ""
    project_id: str = ""


class ProcurementResult(ProcurementFlags):
    main_agent: str = ""
    deep_agent: str = ""
    compare_xlsx: str = ""
    steerco_ppt: str = ""
    xlsx_status: str = ""
    ppt_status: str = ""
    xlsx_href: str = ""
    ppt_href: str = ""


class InvokeRequest(BaseModel):
    request: str = ""
    procurement: ProcurementFlags = Field(default_factory=ProcurementFlags)
    thread_id: str = ""
    resume: Any | None = None
    checkpoint_id: str | None = None
    capability: str = ""
    project_id: str = ""


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


class ProjectRunRequest(BaseModel):
    capability: str
    message: str = ""
    thread_id: str = ""
