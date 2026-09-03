from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._markdown_convertor import MarkdownTableBuilder
from .models import ArtifactDocument, BlockType, ContentBlock, SourceLocation

IMAGE_PLACEHOLDER = re.compile(r"^\[(image|chart)\b", re.IGNORECASE)
PROSE_TYPES = frozenset(
    {
        BlockType.HEADING,
        BlockType.TEXT,
        BlockType.LIST,
        BlockType.OCR,
        BlockType.NOTE,
    }
)
TABLE_TYPES = frozenset({BlockType.TABLE})
SOLO_TYPES = frozenset({BlockType.CHART})


@dataclass(frozen=True)
class ChunkOptions:
    target_tokens: int = 800
    max_tokens: int = 1200


@dataclass
class DocumentChunk:
    ordinal: int
    chunk_type: str
    text: str
    token_count: int
    heading_path: list[str] = field(default_factory=list)
    block_ids: list[str] = field(default_factory=list)
    location: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "chunk_type": self.chunk_type,
            "text": self.text,
            "token_count": self.token_count,
            "heading_path": list(self.heading_path),
            "block_ids": list(self.block_ids),
            "location": dict(self.location),
        }


def estimate_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 4)


def chunk_document(
    document: ArtifactDocument,
    options: ChunkOptions | None = None,
) -> list[DocumentChunk]:
    options = options or ChunkOptions()
    filename = _filename(document)
    emitted: list[DocumentChunk] = []
    prose_group: list[ContentBlock] = []

    def flush_prose() -> None:
        if not prose_group:
            return
        emitted.append(_make_prose_chunk(prose_group, filename, len(emitted)))
        prose_group.clear()

    for block in document.blocks:
        if _is_skippable(block):
            continue
        if block.type in TABLE_TYPES:
            flush_prose()
            emitted.extend(
                _split_table_chunks(block, filename, options, start_ordinal=len(emitted))
            )
            continue
        if block.type in SOLO_TYPES:
            flush_prose()
            emitted.append(_make_solo_chunk(block, filename, len(emitted)))
            continue
        if block.type not in PROSE_TYPES:
            continue
        if prose_group and (
            _boundary_key(block) != _boundary_key(prose_group[0])
            or _prose_tokens(prose_group + [block], filename) > options.max_tokens
        ):
            flush_prose()
        prose_group.append(block)
        if _prose_tokens(prose_group, filename) >= options.target_tokens:
            flush_prose()

    flush_prose()
    return emitted


def _filename(document: ArtifactDocument) -> str:
    name = (document.metadata.filename or "").strip()
    if name:
        return Path(name).name
    if document.source:
        return Path(document.source).name
    return "document"


def _is_skippable(block: ContentBlock) -> bool:
    if block.type == BlockType.IMAGE:
        return True
    text = (block.text or "").strip()
    if IMAGE_PLACEHOLDER.match(text):
        return True
    if block.type == BlockType.TABLE:
        return not (block.table or text)
    return not text


def _boundary_key(block: ContentBlock) -> tuple[int | None, str | None, tuple[str, ...]]:
    return (
        block.location.slide,
        block.location.sheet,
        tuple(block.heading_path),
    )


def _breadcrumb(
    filename: str,
    heading_path: list[str],
    location: SourceLocation | None = None,
) -> str:
    label = f"[{filename}]"
    if heading_path:
        return f"{label} {' > '.join(heading_path)}"
    if location is not None and location.sheet:
        return f"{label} {location.sheet}"
    if location is not None and location.slide is not None:
        return f"{label} Slide {location.slide}"
    return label


def _retrieval_text(prefix: str, body: str) -> str:
    body = body.strip()
    if not body:
        return prefix
    return f"{prefix}\n{body}"


def _prose_body(blocks: list[ContentBlock]) -> str:
    parts = [block.text.strip() for block in blocks if block.text.strip()]
    return "\n\n".join(parts)


def _prose_tokens(blocks: list[ContentBlock], filename: str) -> int:
    if not blocks:
        return 0
    prefix = _breadcrumb(filename, list(blocks[0].heading_path), blocks[0].location)
    return estimate_tokens(_retrieval_text(prefix, _prose_body(blocks)))


def _make_prose_chunk(
    blocks: list[ContentBlock],
    filename: str,
    ordinal: int,
) -> DocumentChunk:
    heading_path = list(blocks[0].heading_path)
    text = _retrieval_text(
        _breadcrumb(filename, heading_path, blocks[0].location),
        _prose_body(blocks),
    )
    return DocumentChunk(
        ordinal=ordinal,
        chunk_type="text",
        text=text,
        token_count=estimate_tokens(text),
        heading_path=heading_path,
        block_ids=_block_ids(blocks),
        location=_span_location(blocks),
    )


def _make_solo_chunk(block: ContentBlock, filename: str, ordinal: int) -> DocumentChunk:
    heading_path = list(block.heading_path)
    text = _retrieval_text(
        _breadcrumb(filename, heading_path, block.location),
        block.text.strip(),
    )
    return DocumentChunk(
        ordinal=ordinal,
        chunk_type="text",
        text=text,
        token_count=estimate_tokens(text),
        heading_path=heading_path,
        block_ids=_block_ids([block]),
        location=_span_location([block]),
    )


def _split_table_chunks(
    block: ContentBlock,
    filename: str,
    options: ChunkOptions,
    *,
    start_ordinal: int,
) -> list[DocumentChunk]:
    rows = _table_rows(block)
    heading_path = list(block.heading_path)
    prefix = _breadcrumb(filename, heading_path, block.location)
    builder = MarkdownTableBuilder()

    def render(subset: list[list[str]]) -> str:
        return _retrieval_text(prefix, builder.build(subset))

    if not rows:
        text = _retrieval_text(prefix, block.text.strip())
        return [
            DocumentChunk(
                ordinal=start_ordinal,
                chunk_type="table",
                text=text,
                token_count=estimate_tokens(text),
                heading_path=heading_path,
                block_ids=_block_ids([block]),
                location=_span_location([block]),
            )
        ]

    if estimate_tokens(render(rows)) <= options.max_tokens or len(rows) == 1:
        text = render(rows)
        return [
            DocumentChunk(
                ordinal=start_ordinal,
                chunk_type="table",
                text=text,
                token_count=estimate_tokens(text),
                heading_path=heading_path,
                block_ids=_block_ids([block]),
                location=_span_location([block]),
            )
        ]

    header, body = rows[0], rows[1:]
    groups: list[list[list[str]]] = []
    current = [header]
    for row in body:
        candidate = current + [row]
        if estimate_tokens(render(candidate)) > options.max_tokens and len(current) > 1:
            groups.append(current)
            current = [header, row]
        else:
            current = candidate
    groups.append(current)

    chunks: list[DocumentChunk] = []
    for offset, group in enumerate(groups):
        text = render(group)
        chunks.append(
            DocumentChunk(
                ordinal=start_ordinal + offset,
                chunk_type="table",
                text=text,
                token_count=estimate_tokens(text),
                heading_path=heading_path,
                block_ids=_block_ids([block]),
                location=_span_location([block]),
            )
        )
    return chunks


def _table_rows(block: ContentBlock) -> list[list[str]]:
    if block.table:
        return [[("" if cell is None else str(cell)) for cell in row] for row in block.table]
    if not block.text.strip():
        return []
    return [line.split(" | ") for line in block.text.splitlines() if line.strip()]


def _block_ids(blocks: list[ContentBlock]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        ident = block.block_id or block.id
        if not ident or ident in seen:
            continue
        seen.add(ident)
        ids.append(ident)
    return ids


def _span_location(blocks: list[ContentBlock]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    pages = [block.location.page for block in blocks if block.location.page is not None]
    if pages:
        payload["page"] = pages[0]
        if pages[-1] != pages[0]:
            payload["page_end"] = pages[-1]
    slides = [block.location.slide for block in blocks if block.location.slide is not None]
    if slides:
        payload["slide"] = slides[0]
    sheets = [block.location.sheet for block in blocks if block.location.sheet]
    if sheets:
        payload["sheet"] = sheets[0]
    ranges = [block.location.cell_range for block in blocks if block.location.cell_range]
    if ranges:
        payload["cell_range"] = ranges[0]
    same_page = bool(pages) and len(set(pages)) == 1
    boxes = [block.location.bbox for block in blocks if block.location.bbox]
    if len(boxes) == 1:
        payload["bbox"] = [round(float(item), 1) for item in boxes[0]]
    elif boxes and same_page:
        payload["bbox"] = [
            round(float(min(box[0] for box in boxes)), 1),
            round(float(min(box[1] for box in boxes)), 1),
            round(float(max(box[2] for box in boxes)), 1),
            round(float(max(box[3] for box in boxes)), 1),
        ]
    return payload
