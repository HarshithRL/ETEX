"""Extract visible text and reasoning from LangChain / Gateway message chunks."""

from __future__ import annotations

from typing import Any


def split_model_content(content: Any) -> tuple[str, str]:
    """Return (visible_text, reasoning_text) from raw model content."""
    if content is None:
        return "", ""
    if isinstance(content, str):
        stripped = content.strip()
        if stripped.startswith("[{") and '"reasoning"' in stripped:
            return "", ""
        return content.strip(), ""
    if not isinstance(content, list):
        return "", ""

    texts: list[str] = []
    reasons: list[str] = []
    for part in content:
        if isinstance(part, str):
            texts.append(part)
            continue
        if not isinstance(part, dict):
            block_type = getattr(part, "type", None)
            if block_type in {"reasoning", "thinking"}:
                text = getattr(part, "text", None)
                if text:
                    reasons.append(str(text))
            elif block_type in {"text", "output_text"}:
                text = getattr(part, "text", None)
                if text:
                    texts.append(str(text))
            continue

        block_type = part.get("type")
        if block_type in {"reasoning", "thinking"}:
            value = _reasoning_from_block(part)
            if value:
                reasons.append(value)
        elif block_type in {"text", "output_text"}:
            value = str(part.get("text") or "")
            if value:
                texts.append(value)

    visible = "".join(texts).strip()
    reasoning = "\n".join(r for r in reasons if r).strip()
    return visible, reasoning


def visible_text_from_message(msg: Any) -> str:
    """User-visible reply text (skips reasoning blocks)."""
    if msg is None:
        return ""
    if isinstance(msg, dict):
        content = msg.get("content")
        if content is None:
            return ""
        text, _ = split_model_content(content)
        return text

    text_accessor = getattr(msg, "text", None)
    if text_accessor is not None:
        value = str(text_accessor)
        if value:
            return value

    text, _ = split_model_content(getattr(msg, "content", None))
    return text


def reasoning_text_from_message(msg: Any) -> str:
    """Reasoning / thinking blocks when the Gateway emits them."""
    if msg is None:
        return ""
    if isinstance(msg, dict):
        _, reasoning = split_model_content(msg.get("content"))
        return reasoning

    kwargs = getattr(msg, "additional_kwargs", None) or {}
    if isinstance(kwargs, dict) and kwargs.get("reasoning"):
        return str(kwargs["reasoning"])

    _, reasoning = split_model_content(getattr(msg, "content", None))
    return reasoning


def normalize_assistant_message(msg: Any) -> Any:
    """Rewrite list-shaped content to str; stash reasoning in additional_kwargs."""
    if msg is None:
        return msg

    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content")

    text, reasoning = split_model_content(content)

    if hasattr(msg, "model_copy"):
        updates: dict[str, Any] = {"content": text}
        if reasoning:
            kwargs = dict(getattr(msg, "additional_kwargs", None) or {})
            kwargs["reasoning"] = reasoning
            updates["additional_kwargs"] = kwargs
        return msg.model_copy(update=updates)

    if isinstance(msg, dict):
        normalized = dict(msg)
        normalized["content"] = text
        if reasoning:
            kwargs = dict(normalized.get("additional_kwargs") or {})
            kwargs["reasoning"] = reasoning
            normalized["additional_kwargs"] = kwargs
        return normalized

    try:
        msg.content = text
        if reasoning:
            kwargs = dict(getattr(msg, "additional_kwargs", None) or {})
            kwargs["reasoning"] = reasoning
            msg.additional_kwargs = kwargs
    except (AttributeError, TypeError):
        pass
    return msg


def latest_assistant_text(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        role = getattr(msg, "type", None)
        if role is None and isinstance(msg, dict):
            role = msg.get("role")
        if role in {"ai", "assistant"}:
            text = visible_text_from_message(msg)
            if text.strip():
                return text
    return ""


def _reasoning_from_block(block: dict[str, Any]) -> str:
    parts: list[str] = []
    summary = block.get("summary")
    if isinstance(summary, list):
        for item in summary:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("reasoning") or ""))
            elif isinstance(item, str):
                parts.append(item)
    val = str(
        block.get("text")
        or block.get("reasoning")
        or block.get("thinking")
        or block.get("summary")
        or ""
    )
    if val and val not in parts:
        parts.append(val)
    return "".join(parts)
