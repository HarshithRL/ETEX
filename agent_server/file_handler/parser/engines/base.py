"""Engine protocol for document → Markdown conversion."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from agent_server.file_handler.parser.types import SupportedFormat


class ParseEngine(Protocol):
    """Convert a supported office/PDF file into Markdown text."""

    name: str

    def supports(self, fmt: SupportedFormat) -> bool:
        """Return True if this engine can handle ``fmt``."""
        ...

    def parse(self, path: Path, fmt: SupportedFormat) -> str:
        """Return Markdown for ``path``. Raise on hard failure."""
        ...
