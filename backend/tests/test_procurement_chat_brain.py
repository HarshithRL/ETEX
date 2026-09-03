"""Workspace chat → AI Brain proxy mapping tests."""

from __future__ import annotations

import json

import httpx

from services.brain_client import invocations_body, invoke_body, parse_sse_frame
from services.procurement_chat import (
    StreamAcc,
    iter_workspace_chat_events,
    map_brain_event,
    sse_format,
)


def test_invocations_body_forces_deepagent_off():
    body = invocations_body("compare vendors", "proj-1")
    assert body["stream"] is True
    assert body["custom_inputs"]["thread_id"] == "proj-1"
    assert body["custom_inputs"]["procurement"] == {
        "mainagent": True,
        "deepagent": False,
        "project_id": "proj-1",
    }


def test_invoke_body_forces_deepagent_off():
    body = invoke_body("hello", "proj-1")
    assert body["procurement"]["mainagent"] is True
    assert body["procurement"]["deepagent"] is False
    assert body["procurement"]["project_id"] == "proj-1"
    assert body["project_id"] == "proj-1"


def test_map_answer_delta_to_token():
    acc = StreamAcc()
    events = list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "Hello",
                "custom_outputs": {"kind": "answer", "node": "main_agent"},
            },
            acc,
        )
    )
    assert events == [{"type": "token", "text": "Hello"}]
    assert acc.answer == "Hello"


def test_map_thought_delta_and_done_payload():
    acc = StreamAcc()
    steps = list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "",
                "custom_outputs": {"kind": "thought", "node": "skip_deepagent"},
            },
            acc,
        )
    )
    assert steps[0]["type"] == "thought"
    assert steps[0]["kind"] == "step"
    assert steps[0]["label"] == "Skipped Deep Agents"

    list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "Why: ",
                "custom_outputs": {"kind": "thought", "node": "main_agent"},
            },
            acc,
        )
    )
    list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "scope",
                "custom_outputs": {"kind": "thought", "node": "main_agent"},
            },
            acc,
        )
    )
    list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "Done.",
                "custom_outputs": {"kind": "answer", "node": "main_agent"},
            },
            acc,
        )
    )
    done = list(
        map_brain_event(
            {
                "type": "response.output_item.done",
                "item": {
                    "content": [{"type": "output_text", "text": "Done."}],
                },
                "custom_outputs": {"kind": "answer", "final": True},
            },
            acc,
        )
    )
    assert done[0]["type"] == "done"
    assert done[0]["text"] == "Done."
    kinds = [item["kind"] for item in done[0]["thoughts"]]
    assert kinds == ["step", "thought"]
    reasoning = next(item for item in done[0]["thoughts"] if item["kind"] == "thought")
    assert reasoning["label"] == "Thought"
    assert reasoning["detail"] == "Why: scope"
    assert "Done." not in reasoning["detail"]


def test_empty_main_agent_thought_is_not_a_step():
    acc = StreamAcc()
    events = list(
        map_brain_event(
            {
                "type": "response.output_text.delta",
                "delta": "",
                "custom_outputs": {"kind": "thought", "node": "main_agent"},
            },
            acc,
        )
    )
    assert events == []
    assert acc.thoughts == []


def test_map_brain_down_iter_yields_error(monkeypatch):
    monkeypatch.setattr(
        "services.procurement_chat._prepare",
        lambda *args, **kwargs: ({"id": "p1", "name": "untitled"}, "hello"),
    )

    def boom(request_text: str, thread_id: str):
        request = httpx.Request("POST", "http://127.0.0.1:8004/invocations")
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(
        "services.procurement_chat.brain_client.iter_invocations_sse",
        boom,
    )
    events = list(iter_workspace_chat_events("p1", "owner-1", "hello"))
    assert events[0]["type"] == "error"
    assert "ConnectError" in events[0]["detail"]


def test_iter_workspace_chat_maps_stream(monkeypatch):
    monkeypatch.setattr(
        "services.procurement_chat._prepare",
        lambda *args, **kwargs: ({"id": "p1", "name": "untitled"}, "hello"),
    )

    def frames(request_text: str, thread_id: str):
        assert request_text == "hello"
        assert thread_id == "p1"
        yield {
            "type": "response.output_text.delta",
            "delta": "Hi",
            "custom_outputs": {"kind": "answer", "node": "main_agent"},
        }
        yield {
            "type": "response.output_item.done",
            "item": {"content": [{"text": "Hi there"}]},
            "custom_outputs": {"kind": "answer", "final": True},
        }

    monkeypatch.setattr(
        "services.procurement_chat.brain_client.iter_invocations_sse",
        frames,
    )
    events = list(iter_workspace_chat_events("p1", "owner-1", "hello"))
    types = [item["type"] for item in events]
    assert types == ["token", "done"]
    assert events[0]["text"] == "Hi"
    assert events[1]["text"] == "Hi there"


def test_parse_sse_frame_and_format():
    parsed = parse_sse_frame(
        'data: {"type": "response.output_text.delta", "delta": "x"}'
    )
    assert parsed["delta"] == "x"
    assert parse_sse_frame("data: [DONE]") is None
    frame = sse_format({"type": "token", "text": "Hi"})
    assert frame.startswith("event: token\n")
    payload = json.loads(frame.split("data: ", 1)[1].strip())
    assert payload == {"text": "Hi"}


def test_message_required(monkeypatch):
    def missing(*args, **kwargs):
        raise ValueError("message is required")

    monkeypatch.setattr("services.procurement_chat._prepare", missing)
    events = list(iter_workspace_chat_events("p1", "owner-1", "  "))
    assert events == [{"type": "error", "detail": "message is required"}]
