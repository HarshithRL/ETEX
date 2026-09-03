from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from ai_brain.core.procurement_ai.knowledge import (
    knowledge_prompt_block,
    search_chunks,
)
from ai_brain.core.procurement_ai.subagents.main_agent import (
    ProcuraContext,
    _runtime_project_id,
    get_procura_main_agent,
    project_id_for_agent,
    procura_kb_prompt,
)


class _Project:
    id = "proj-demo"
    code = "PR-100"
    name = "SWIFT CSP assessment"
    business_process = "Indirect"
    category = "SWIFT CSCF"
    description = "Professional services days"


class _Artifact:
    def __init__(self, artifact_id: str, name: str):
        self.id = artifact_id
        self.original_name = name
        self.parse_status = "ok"


class _Chunk:
    def __init__(self, artifact_id: str, text: str, ordinal: int = 0, page: int = 1):
        self.id = f"c-{ordinal}"
        self.artifact_id = artifact_id
        self.ordinal = ordinal
        self.text = text
        self.location_json = f'{{"page": {page}}}'
        self.heading_path_json = '["Pricing"]'


def test_search_ranks_price_chunk_first():
    artifacts = [
        _Artifact("a1", "EY_proposal.pdf"),
        _Artifact("a2", "KPMG_proposal.pdf"),
    ]
    chunks = [
        _Chunk("a1", "Team bios and office locations in Brussels.", ordinal=0),
        _Chunk("a1", "Day rate is 1,250 EUR for the senior manager.", ordinal=1, page=4),
        _Chunk("a2", "Approach to SWIFT CSP independent assessment.", ordinal=2),
    ]
    hits = search_chunks("what is the day rate", artifacts, chunks)
    assert hits
    assert hits[0]["file"] == "EY_proposal.pdf"
    assert hits[0]["locator"] == "p.4"
    assert "1,250 EUR" in hits[0]["text"]


def test_search_falls_back_when_query_has_no_overlap():
    artifacts = [_Artifact("a1", "EY_proposal.pdf")]
    chunks = [_Chunk("a1", "SWIFT CSP independent assessment proposal.", ordinal=0)]
    hits = search_chunks("zzzz-no-match", artifacts, chunks)
    assert len(hits) == 1
    assert "SWIFT CSP" in hits[0]["text"]


def test_knowledge_prompt_block_empty_project_id():
    assert knowledge_prompt_block("", "hello") == ""
    assert knowledge_prompt_block("   ", "hello") == ""


def test_knowledge_prompt_block_includes_excerpts(monkeypatch):
    def fake_load(_pid: str):
        return _Project(), [_Artifact("a1", "EY_proposal.pdf")], [
            _Chunk("a1", "Blended rate 900 EUR per day.", ordinal=0, page=2)
        ]

    monkeypatch.setattr(
        "ai_brain.core.procurement_ai.knowledge.load_context",
        fake_load,
    )
    block = knowledge_prompt_block("proj-demo", "blended rate")
    assert "## Project knowledge base" in block
    assert "PR-100" in block
    assert "EY_proposal.pdf" in block
    assert "p.2" in block
    assert "900 EUR" in block


def test_project_id_for_agent_prefers_state_then_thread():
    assert project_id_for_agent({"project_id": "p-state"}, None) == "p-state"
    assert (
        project_id_for_agent(
            {"procurement": {"project_id": "p-flag"}},
            {"configurable": {"thread_id": "p-thread"}},
        )
        == "p-flag"
    )
    assert (
        project_id_for_agent({}, {"configurable": {"thread_id": "p-thread"}})
        == "p-thread"
    )


def test_runtime_project_id_prefers_context_over_thread():
    request = SimpleNamespace(
        runtime=SimpleNamespace(
            context=ProcuraContext(project_id="p-ctx"),
            config={"configurable": {"thread_id": "p-thread"}},
        )
    )
    assert _runtime_project_id(request) == "p-ctx"
    request.runtime.context = ProcuraContext(project_id="")
    assert _runtime_project_id(request) == "p-thread"


def test_create_agent_wires_kb_middleware(monkeypatch):
    get_procura_main_agent.cache_clear()
    captured: dict = {}

    def fake_create_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="agent")

    fake_config = ModuleType("ai_brain.core.config")
    fake_config.get_llm = lambda **_k: object()
    monkeypatch.setitem(sys.modules, "ai_brain.core.config", fake_config)
    monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)
    try:
        agent = get_procura_main_agent()
        assert agent.name == "agent"
        assert captured["tools"] == []
        assert captured["context_schema"] is ProcuraContext
        assert procura_kb_prompt in captured["middleware"]
    finally:
        get_procura_main_agent.cache_clear()
