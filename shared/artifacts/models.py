from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

COORD_PDF_POINTS = "pdf_points_top_left"


class ArtifactType(str, Enum):
    PDF = "pdf"
    PPT = "ppt"
    EXCEL = "excel"
    WORD = "word"


class BlockType(str, Enum):
    HEADING = "heading"
    TEXT = "text"
    LIST = "list"
    TABLE = "table"
    IMAGE = "image"
    CHART = "chart"
    OCR = "ocr"
    NOTE = "note"


@dataclass(frozen=True)
class ParseOptions:
    password: str | None = None
    include_tables: bool = True
    include_images: bool = False
    include_hidden_sheets: bool = False
    max_pages: int | None = None
    use_ocr: bool = False


@dataclass
class SourceLocation:
    page: int | None = None
    slide: int | None = None
    sheet: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    page_width: float | None = None
    page_height: float | None = None
    paragraph_index: int | None = None
    table_index: int | None = None
    row: int | None = None
    col: int | None = None
    cell_range: str | None = None
    shape_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if value is None:
                continue
            if key == "bbox":
                payload[key] = [round(float(item), 1) for item in value]
            elif key in {"page_width", "page_height"}:
                payload[key] = round(float(value), 1)
            else:
                payload[key] = value
        return payload


@dataclass
class PageInfo:
    page: int
    width: float
    height: float
    rotation: int = 0
    kind: str = "mixed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "width": round(float(self.width), 1),
            "height": round(float(self.height), 1),
            "rotation": int(self.rotation),
            "kind": self.kind,
        }


@dataclass
class OutlineItem:
    title: str
    page: int | None
    level: int
    block_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "page": self.page,
            "level": self.level,
            "block_id": self.block_id,
        }


@dataclass
class ContentBlock:
    id: str
    type: BlockType
    text: str
    location: SourceLocation = field(default_factory=SourceLocation)
    table: list[list[str]] | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    block_id: str = ""
    level: int | None = None
    heading_path: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "block_id": self.block_id,
            "type": self.type.value,
            "level": self.level,
            "heading_path": list(self.heading_path),
            "text": self.text,
            "location": self.location.to_dict(),
        }
        if self.table is not None:
            payload["table"] = self.table
        if self.extra:
            payload["extra"] = self.extra
        return payload


@dataclass
class ArtifactMetadata:
    filename: str
    artifact_type: ArtifactType
    mime_type: str | None = None
    title: str | None = None
    author: str | None = None
    created: str | None = None
    modified: str | None = None
    page_count: int | None = None
    slide_count: int | None = None
    sheet_count: int | None = None
    encrypted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "artifact_type": self.artifact_type.value,
            "mime_type": self.mime_type,
            "title": self.title,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
            "page_count": self.page_count,
            "slide_count": self.slide_count,
            "sheet_count": self.sheet_count,
            "encrypted": self.encrypted,
        }


@dataclass
class ArtifactDocument:
    source: str
    artifact_type: ArtifactType
    metadata: ArtifactMetadata
    blocks: list[ContentBlock] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    markdown: str = ""
    artifact_id: str = ""
    coord_system: str = ""
    pages: list[PageInfo] = field(default_factory=list)
    outline: list[OutlineItem] = field(default_factory=list)

    def plain_text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text.strip()).strip()

    def md_text(self) -> str:
        if self.markdown.strip():
            return self.markdown.rstrip("\n")
        from ._markdown_convertor import MarkdownConvertor

        return MarkdownConvertor().convert(self).rstrip("\n")

    def tables(self) -> list[ContentBlock]:
        return [block for block in self.blocks if block.type == BlockType.TABLE]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "source": self.source,
            "artifact_type": self.artifact_type.value,
            "coord_system": self.coord_system,
            "metadata": self.metadata.to_dict(),
            "pages": [page.to_dict() for page in self.pages],
            "outline": [item.to_dict() for item in self.outline],
            "blocks": [block.to_dict() for block in self.blocks],
            "warnings": list(self.warnings),
            "markdown": self.md_text(),
        }


MIME_BY_TYPE = {
    ArtifactType.PDF: "application/pdf",
    ArtifactType.PPT: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ArtifactType.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ArtifactType.WORD: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def source_name(source: str | Path | bytes, filename: str | None) -> str:
    if filename:
        return Path(filename).name
    if isinstance(source, (str, Path)):
        return Path(source).name
    return "memory.bin"
