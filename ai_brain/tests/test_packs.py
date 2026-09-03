from __future__ import annotations

from pathlib import Path

from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.packs.compare_xlsx import build_comparison_xlsx
from ai_brain.core.procurement_ai.packs.steerco_ppt import build_steerco_ppt
from ai_brain.core.procurement_ai.process_type import classify_process_type


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


def test_classify_swift_as_it_services():
    assert classify_process_type(
        business_process="Indirect",
        category="SWIFT CSCF",
        name="SWIFT CSP",
    ) == "indirect_it_services"


def test_classify_direct_screws():
    assert classify_process_type(business_process="Direct", name="TG screws") == "direct_tg"


def test_pack_builders_write_files(tmp_path, monkeypatch):
    monkeypatch.setenv("MATE_PROJECTS_DATA_ROOT", str(tmp_path))
    insights = build_insight_payload(_Project(), [_Artifact()], [])
    assert insights["process_type"] == "indirect_it_services"
    assert insights["decision"]["can_build_xlsx"] is True
    xlsx = build_comparison_xlsx("proj-demo", insights, thread_id="t1")
    assert xlsx["status"] == "ready"
    assert Path(xlsx["path"]).exists()
    ppt = build_steerco_ppt("proj-demo", thread_id="t1")
    assert ppt["status"] == "ready"
    assert Path(ppt["path"]).exists()
