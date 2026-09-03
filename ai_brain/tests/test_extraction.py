from __future__ import annotations

from ai_brain.core.procurement_ai.capabilities import normalize_capability
from ai_brain.core.procurement_ai.extraction import (
    normalize_facts,
    overlay_insights,
    parse_facts_json,
)
from ai_brain.core.procurement_ai.procura_graph import after_start


def test_extract_capability_routes_to_deepagent():
    assert normalize_capability("extract") == "extract"
    assert normalize_capability("facts") == "extract"
    state = {
        "request": "extract",
        "project_id": "p1",
        "capability": "extract",
        "procurement": {"capability": "extract", "project_id": "p1"},
    }
    assert after_start(state) == "deepagent"


def test_missing_never_becomes_zero():
    facts = parse_facts_json(
        '{"vendors":[{"name":"EY","external_cost":"","day_rate":null,"internal_days":"missing"}]}'
    )
    ey = facts["vendors"][0]
    assert ey["external_cost"] == "missing"
    assert ey["day_rate"] == "missing"
    assert ey["internal_days"] == "missing"


def test_overlay_keeps_filename_vendor_when_extract_silent():
    insights = {
        "vendors": [{"name": "EY", "headline": "from filename", "artifact_count": 1}],
        "requirements": {"items": []},
        "decision": {"blockers": []},
    }
    facts = normalize_facts({"vendors": [{"name": "EY", "headline": "cited line", "external_cost": 42000}]})
    out = overlay_insights(insights, facts)
    assert out["vendors"][0]["headline"] == "cited line"
    assert out["vendors"][0]["external_cost"] == 42000
    assert out["comparison_facts"] is True
