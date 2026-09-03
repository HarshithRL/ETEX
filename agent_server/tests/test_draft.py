"""Tests for draft validation."""

from __future__ import annotations

from agent_server.core.subagents.procure_agent.draft import (
    draft_has_meaningful_fields,
    question_for_reason,
    validate_draft,
)


def test_validate_draft_parse_failed():
    result = validate_draft(None)
    assert not result.ok
    assert result.reason == "parse_failed"


def test_validate_draft_empty_name():
    result = validate_draft({"name": "", "workflowEntryPoint": "Sourcing"})
    assert not result.ok
    assert result.reason == "empty_name"


def test_validate_draft_missing_workflow():
    result = validate_draft({"name": "Test project", "workflowEntryPoint": ""})
    assert not result.ok
    assert result.reason == "missing_workflow"


def test_validate_draft_ok():
    result = validate_draft(
        {"name": "Test project", "workflowEntryPoint": "Sourcing"},
    )
    assert result.ok
    assert result.reason == ""


def test_draft_has_meaningful_fields():
    assert not draft_has_meaningful_fields({"name": "", "workflowEntryPoint": ""})
    assert draft_has_meaningful_fields({"name": "X", "workflowEntryPoint": ""})


def test_real_draft_fields_skips_untitled_and_empty():
    from agent_server.core.subagents.procure_agent.draft import real_draft_fields

    assert real_draft_fields(None) == {}
    assert real_draft_fields({"name": "untitled", "workflowEntryPoint": ""}) == {}
    assert real_draft_fields(
        {"name": "Office Supplies", "workflowEntryPoint": "untitled", "businessProcess": "Direct"}
    ) == {"name": "Office Supplies", "businessProcess": "Direct"}


def test_question_for_reason():
    assert "call" in question_for_reason("empty_name").lower()
    assert "workflow" in question_for_reason("missing_workflow").lower()
