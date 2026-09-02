"""Shared LangGraph state for Mate parent + procure_ai subgraphs."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from langchain.agents import AgentState


class ProjectDraft(TypedDict, total=False):
    name: str
    workflowEntryPoint: str
    businessProcess: str
    requester: str
    dept: str
    targetSpend: str
    category: str
    awardHorizon: str
    region: str
    description: str
    brief: str
    requirements: list[str | dict[str, str]]


class TokenUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class MateAgentState(AgentState):
    """Parent and procure_ai share these keys so the subgraph can be a node."""

    route: NotRequired[str]
    thread_id: NotRequired[str]
    project_draft: NotRequired[ProjectDraft]
    draft_status: NotRequired[str]
    draft_reason: NotRequired[str]
    draft_question: NotRequired[str]
    visible_reply: NotRequired[str]
    usage: NotRequired[TokenUsage]
    thoughts: NotRequired[str]
