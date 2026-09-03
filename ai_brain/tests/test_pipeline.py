from __future__ import annotations

from ai_brain.core.procurement_ai.capabilities import normalize_capability
from ai_brain.core.procurement_ai.pipeline import (
    build_knowledge_base,
    build_knowledge_graph,
)
from ai_brain.core.procurement_ai.procura_graph import after_start, merge_dicts


class _Project:
    id = "proj-demo"
    code = "PR-100"
    name = "SWIFT CSP assessment"
    business_process = "Indirect"
    category = "SWIFT CSCF"
    description = "Professional services days"


class _Artifact:
    id = "a1"
    original_name = "EY_proposal.pdf"
    parse_status = "ok"


def _state(capability: str, **procurement):
    return {
        "request": "run",
        "project_id": "proj-demo",
        "capability": capability,
        "procurement": {"capability": capability, "project_id": "proj-demo", **procurement},
    }


def test_ingest_aliases_route_to_list_artifacts():
    for raw in ("ingest", "parse", "upload", "kb_build", "pipeline"):
        assert normalize_capability(raw) in {"ingest", "kb_build"}
        assert after_start(_state(normalize_capability(raw))) == "list_artifacts"


def test_packs_stay_on_own_nodes():
    assert after_start(_state("compare_xlsx")) == "compare_xlsx"
    assert after_start(_state("steerco_ppt")) == "steerco_ppt"


def test_parse_fanout_one_send_per_file():
    from ai_brain.core.procurement_ai.subagents.ingest import fanout_parse

    sends = fanout_parse(_state("ingest", artifact_ids=["a", "b", "c"]))
    assert [item.node for item in sends] == ["parse_artifact", "parse_artifact", "parse_artifact"]
    ids = [item.arg["procurement"]["artifact_id"] for item in sends]
    assert ids == ["a", "b", "c"]


def test_parse_fanout_empty_joins_assemble():
    from ai_brain.core.procurement_ai.subagents.ingest import fanout_parse

    sends = fanout_parse(_state("ingest", artifact_ids=[]))
    assert len(sends) == 1
    assert sends[0].node == "assemble_parse"


def test_merge_dicts_concatenates_parse_results():
    left = {"parse_results": [{"artifact_id": "a"}]}
    right = {"parse_results": [{"artifact_id": "b"}]}
    merged = merge_dicts(left, right)
    assert [row["artifact_id"] for row in merged["parse_results"]] == ["a", "b"]


def test_kb_and_kg_are_independent_payloads():
    kb = build_knowledge_base(_Project(), [_Artifact()], [])
    kg = build_knowledge_graph(_Project(), [_Artifact()], [])
    assert kb["kind"] == "knowledge_base"
    assert kg["kind"] == "knowledge_graph"
    assert any(node["type"] == "Vendor" for node in kg["nodes"])
    assert any(entity["type"] == "Requirement" for entity in kb["entities"])
