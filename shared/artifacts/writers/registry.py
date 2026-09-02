from __future__ import annotations

from ..exceptions import UnsupportedArtifact
from ..models import ArtifactType
from .docx_writer import DocxWriter
from .pdf_writer import PdfWriter
from .pptx_writer import PptxWriter
from .xlsx_writer import XlsxWriter

_WRITERS = {
    ArtifactType.PDF: PdfWriter,
    ArtifactType.PPT: PptxWriter,
    ArtifactType.EXCEL: XlsxWriter,
    ArtifactType.WORD: DocxWriter,
}


def get_writer(artifact_type: ArtifactType):
    try:
        return _WRITERS[artifact_type]()
    except KeyError as exc:
        raise UnsupportedArtifact(f"No writer registered for type: {artifact_type}") from exc


def writer_for(artifact_type: ArtifactType | str):
    if isinstance(artifact_type, str):
        try:
            artifact_type = ArtifactType(artifact_type.lower())
        except ValueError as exc:
            raise UnsupportedArtifact(f"Unknown artifact type: {artifact_type}") from exc
    return get_writer(artifact_type)
