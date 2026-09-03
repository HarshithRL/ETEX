from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from ai_brain.core.procurement_ai.capabilities import (
    COMPARE_XLSX,
    STEERCO_PPT,
    capability_from_state,
)


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    """Deep-merge nested control/output dicts so node updates do not wipe flags."""
    left = dict(left or {})
    right = dict(right or {})
    out = left
    for key, value in right.items():
        existing = out.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            out[key] = merge_dicts(existing, value)
        else:
            out[key] = value
    return out


class ProcurementState(TypedDict, total=False):
    mainagent: bool
    deepagent: bool
    capability: str
    project_id: str
    main_agent: str
    deep_agent: str
    compare_xlsx: str
    steerco_ppt: str
    xlsx_status: str
    ppt_status: str
    xlsx_href: str
    ppt_href: str


class ProcuraState(TypedDict):
    request: str
    project_id: str
    capability: str
    procurement: Annotated[ProcurementState, merge_dicts]


def _procurement(state: dict) -> dict:
    return state.get("procurement") or {}


def mainagent_on(state: dict) -> bool:
    return bool(_procurement(state).get("mainagent"))


def deepagent_on(state: dict) -> bool:
    return bool(_procurement(state).get("deepagent"))


def procurement_on(state: dict) -> bool:
    if capability_from_state(state):
        return True
    return mainagent_on(state) or deepagent_on(state)


def after_start(
    state: ProcuraState,
) -> Literal["main_agent", "skip_main", "compare_xlsx", "steerco_ppt"]:
    capability = capability_from_state(state)
    if capability == COMPARE_XLSX:
        return "compare_xlsx"
    if capability == STEERCO_PPT:
        return "steerco_ppt"
    return "main_agent" if mainagent_on(state) else "skip_main"


def after_main(state: ProcuraState) -> Literal["deepagent", "skip_deepagent"]:
    return "deepagent" if deepagent_on(state) else "skip_deepagent"


def skip_main(state: ProcuraState) -> dict:
    return {"procurement": {"main_agent": ""}}


def skip_deepagent(state: ProcuraState) -> dict:
    return {"procurement": {"deep_agent": ""}}


def build_procura_ai(*, checkpointer=None):
    from ai_brain.core.procurement_ai.subagents.compare_xlsx import compare_xlsx
    from ai_brain.core.procurement_ai.subagents.deepagents import deepagent
    from ai_brain.core.procurement_ai.subagents.main_agent import main_agent
    from ai_brain.core.procurement_ai.subagents.steerco_ppt import steerco_ppt

    g = StateGraph(ProcuraState)
    g.add_node("main_agent", main_agent)
    g.add_node("skip_main", skip_main)
    g.add_node("deepagent", deepagent)
    g.add_node("skip_deepagent", skip_deepagent)
    g.add_node("compare_xlsx", compare_xlsx)
    g.add_node("steerco_ppt", steerco_ppt)
    g.add_conditional_edges(
        START,
        after_start,
        {
            "main_agent": "main_agent",
            "skip_main": "skip_main",
            "compare_xlsx": "compare_xlsx",
            "steerco_ppt": "steerco_ppt",
        },
    )
    deepagent_next = {"deepagent": "deepagent", "skip_deepagent": "skip_deepagent"}
    g.add_conditional_edges("main_agent", after_main, deepagent_next)
    g.add_conditional_edges("skip_main", after_main, deepagent_next)
    g.add_edge("deepagent", END)
    g.add_edge("skip_deepagent", END)
    g.add_edge("compare_xlsx", END)
    g.add_edge("steerco_ppt", END)
    kwargs: dict = {"name": "procura"}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    return g.compile(**kwargs)
