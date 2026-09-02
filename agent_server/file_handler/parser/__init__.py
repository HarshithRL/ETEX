"""Document → Markdown parser (Docling primary, native fallback)."""

from agent_server.file_handler.parser.router import (
    DocumentParser,
    parse_dir,
    parse_file,
)
from agent_server.file_handler.parser.types import (
    ParseError,
    ParseResult,
    SupportedFormat,
)

__all__ = [
    "DocumentParser",
    "ParseError",
    "ParseResult",
    "SupportedFormat",
    "parse_dir",
    "parse_file",
]
