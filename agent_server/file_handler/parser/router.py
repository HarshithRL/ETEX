"""Route files to Docling first, then native fallback."""

from __future__ import annotations

import time
from pathlib import Path

from agent_server.file_handler.parser.engines.docling_engine import DoclingEngine
from agent_server.file_handler.parser.engines.native_engine import NativeEngine
from agent_server.file_handler.parser.types import (
    EngineName,
    ParseError,
    ParseResult,
    SupportedFormat,
)
from shared.logger_global import bind_context, get_logger

log = get_logger(__name__, service="agent_server")

SUPPORTED_EXTENSIONS = {f".{fmt.value}" for fmt in SupportedFormat}


def _trace_header(path: Path, engine: EngineName) -> str:
    return f"<!-- source: {path.as_posix()} | engine: {engine} -->\n\n"


class DocumentParser:
    """Facade: Docling primary, native fallback."""

    def __init__(
        self,
        *,
        prefer_docling: bool = True,
        docling: DoclingEngine | None = None,
        native: NativeEngine | None = None,
    ) -> None:
        self.prefer_docling = prefer_docling
        self._docling = docling or DoclingEngine()
        self._native = native or NativeEngine()

    def parse_file(self, path: Path | str) -> ParseResult:
        bind_context(workflow="parser.parse_file")
        started = time.perf_counter()
        source = Path(path).expanduser().resolve()
        fmt = SupportedFormat.from_path(source)
        if fmt is None:
            log.warning("unsupported file type path={}", source)
            return ParseResult(
                source_path=source,
                format=SupportedFormat.PDF,
                engine="native",
                markdown="",
                error=f"Unsupported file type: {source.suffix or '(none)'}",
            )
        if not source.is_file():
            log.warning("parse file not found path={}", source)
            return ParseResult(
                source_path=source,
                format=fmt,
                engine="native",
                markdown="",
                error=f"File not found: {source}",
            )

        engines: list[tuple[EngineName, DoclingEngine | NativeEngine]] = []
        if self.prefer_docling:
            engines.append(("docling", self._docling))
            engines.append(("native", self._native))
        else:
            engines.append(("native", self._native))
            engines.append(("docling", self._docling))

        errors: list[str] = []
        for name, engine in engines:
            if not engine.supports(fmt):
                continue
            engine_started = time.perf_counter()
            try:
                body = engine.parse(source, fmt)
                markdown = _trace_header(source, name) + body
                log.info(
                    "parse ok path={} engine={} format={} duration_ms={}",
                    source.name,
                    name,
                    fmt.value,
                    round((time.perf_counter() - engine_started) * 1000, 2),
                )
                return ParseResult(
                    source_path=source,
                    format=fmt,
                    engine=name,
                    markdown=markdown,
                )
            except ParseError as exc:
                errors.append(f"{name}: {exc}")
                log.warning(
                    "parse engine failed path={} engine={} error={} duration_ms={}",
                    source.name,
                    name,
                    exc,
                    round((time.perf_counter() - engine_started) * 1000, 2),
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")
                log.warning(
                    "parse engine error path={} engine={} error={} duration_ms={}",
                    source.name,
                    name,
                    exc,
                    round((time.perf_counter() - engine_started) * 1000, 2),
                )

        log.error(
            "parse failed path={} errors={} duration_ms={}",
            source.name,
            "; ".join(errors),
            round((time.perf_counter() - started) * 1000, 2),
        )
        return ParseResult(
            source_path=source,
            format=fmt,
            engine="native",
            markdown="",
            error="; ".join(errors) or "All engines failed",
        )

    def parse_dir(
        self,
        root: Path | str,
        *,
        recursive: bool = True,
    ) -> list[ParseResult]:
        base = Path(root).expanduser().resolve()
        if not base.is_dir():
            raise FileNotFoundError(f"Not a directory: {base}")

        pattern = "**/*" if recursive else "*"
        paths = sorted(
            p
            for p in base.glob(pattern)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        log.info("parse_dir root={} file_count={}", base, len(paths))
        return [self.parse_file(p) for p in paths]


_default_parser = DocumentParser()


def parse_file(path: Path | str, *, prefer_docling: bool = True) -> ParseResult:
    """Parse one document to Markdown."""
    if prefer_docling is True and _default_parser.prefer_docling:
        return _default_parser.parse_file(path)
    return DocumentParser(prefer_docling=prefer_docling).parse_file(path)


def parse_dir(
    root: Path | str,
    *,
    recursive: bool = True,
    prefer_docling: bool = True,
) -> list[ParseResult]:
    """Parse all supported documents under ``root``."""
    parser = (
        _default_parser
        if prefer_docling is True and _default_parser.prefer_docling
        else DocumentParser(prefer_docling=prefer_docling)
    )
    return parser.parse_dir(root, recursive=recursive)
