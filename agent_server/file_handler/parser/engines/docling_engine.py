"""Docling-backed document → Markdown engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_server.file_handler.parser.types import ParseError, SupportedFormat

_SUPPORTED = frozenset(SupportedFormat)


class DoclingEngine:
    """Primary parser using IBM Docling ``DocumentConverter``."""

    name = "docling"

    def __init__(self) -> None:
        self._converter: Any | None = None
        self._init_error: str | None = None

    def supports(self, fmt: SupportedFormat) -> bool:
        return fmt in _SUPPORTED

    def _get_converter(self) -> Any:
        if self._converter is not None:
            return self._converter
        if self._init_error is not None:
            raise ParseError(f"Docling unavailable: {self._init_error}")
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption

            # Prefer embedded text over OCR for digital PDFs (faster + cleaner MD).
            pdf_options = PdfPipelineOptions(
                do_ocr=False,
                force_backend_text=True,
                do_table_structure=True,
            )
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
                }
            )
            return self._converter
        except Exception as exc:  # noqa: BLE001 — soft-fail to native
            self._init_error = str(exc)
            raise ParseError(
                f"Docling unavailable: {exc}",
                cause=exc,
            ) from exc

    def parse(self, path: Path, fmt: SupportedFormat) -> str:
        if not self.supports(fmt):
            raise ParseError(f"Unsupported format for Docling: {fmt.value}", path=path)
        try:
            converter = self._get_converter()
            result = converter.convert(str(path))
            document = getattr(result, "document", None)
            if document is None:
                raise ParseError("Docling returned no document", path=path)
            markdown = document.export_to_markdown()
            if not isinstance(markdown, str) or not markdown.strip():
                raise ParseError("Docling produced empty markdown", path=path)
            return markdown.strip() + "\n"
        except ParseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ParseError(
                f"Docling convert failed: {exc}",
                path=path,
                cause=exc,
            ) from exc
