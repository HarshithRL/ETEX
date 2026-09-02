"""Tests for Gateway message content splitting."""

from __future__ import annotations

from agent_server.core.message_text import (
    reasoning_text_from_message,
    split_model_content,
    visible_text_from_message,
)


class _FakeMsg:
    def __init__(self, content, additional_kwargs=None):
        self.content = content
        self.additional_kwargs = additional_kwargs or {}
        self.type = "ai"


def test_split_model_content_none():
    assert split_model_content(None) == ("", "")


def test_split_model_content_plain_str():
    assert split_model_content("Hello world") == ("Hello world", "")


def test_split_model_content_text_blocks():
    content = [
        {"type": "text", "text": "Visible "},
        {"type": "output_text", "text": "reply."},
    ]
    assert split_model_content(content) == ("Visible reply.", "")


def test_split_model_content_reasoning_blocks():
    content = [
        {"type": "reasoning", "text": "Thinking step one."},
        {"type": "text", "text": "Answer."},
    ]
    text, reasoning = split_model_content(content)
    assert text == "Answer."
    assert "Thinking step one." in reasoning


def test_split_model_content_reasoning_with_summary():
    content = [
        {
            "type": "reasoning",
            "summary": [{"text": "Summary bit."}],
            "text": "Detail.",
        },
        {"type": "text", "text": "Hi."},
    ]
    text, reasoning = split_model_content(content)
    assert text == "Hi."
    assert "Summary bit." in reasoning
    assert "Detail." in reasoning


def test_split_model_content_mixed_strings_and_blocks():
    content = ["prefix ", {"type": "text", "text": "suffix"}]
    assert split_model_content(content) == ("prefix suffix", "")


def test_visible_text_from_message_dict():
    msg = {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]}
    assert visible_text_from_message(msg) == "Hi"


def test_reasoning_text_from_normalized_message():
    msg = _FakeMsg("visible", additional_kwargs={"reasoning": "internal thought"})
    assert visible_text_from_message(msg) == "visible"
    assert reasoning_text_from_message(msg) == "internal thought"
