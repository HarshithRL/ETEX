"""Shared types for the document parser."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal


class SupportedFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"

    @classmethod
    def from_path(cls, path: Path | str) -> SupportedFormat | None:
        suffix = Path(path).suffix.lower().lstrip(".")
        try:
            return cls(suffix)
        except ValueError:
            return None


EngineName = Literal["docling", "native"]


@dataclass(slots=True)
class ParseResult:
    """Outcome of parsing one document to Markdown."""

    source_path: Path
    format: SupportedFormat
    engine: EngineName
    markdown: str
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.markdown.strip())


class ParseError(Exception):
    """Raised when a single engine cannot parse a file."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message
        self.path = path
        self.cause = cause
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.path is not None:
            return f"{self.message} ({self.path})"
        return self.message
