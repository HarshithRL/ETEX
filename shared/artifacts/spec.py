from __future__ import annotations

"""Create/update IR for the artifact engine.

Agents should emit a JSON ArtifactSpec (same block vocabulary as ContentBlock)
and call ArtifactHandler.create(spec). To edit, parse() the file, then
ArtifactHandler.update(source, ops) with ordered PatchOp dicts targeting
block_id (or SourceLocation fields the parser actually emits: paragraph_index,
shape_id, cell_range, slide, sheet).

Office XML (docx/pptx/xlsx) is patched in place. PDFs are regenerated from a
spec derived from the parsed document — not patched byte-wise.

Unknown ops and missing targets raise ArtifactPatchError (never a silent no-op).
"""

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable

from .exceptions import ArtifactPatchError, ArtifactWriteError, UnsupportedArtifact
from .models import ArtifactType, BlockType, SourceLocation
from .parsers.registry import PARSEABLE_EXTENSIONS

PATCH_OPS = frozenset(
    {
        "replace_text",
        "replace_table",
        "set_cell",
        "insert_block",
        "delete_block",
        "insert_slide",
        "replace_shape_text",
        "set_title",
    }
)

_TYPE_ALIASES = {
    "pdf": ArtifactType.PDF,
    "ppt": ArtifactType.PPT,
    "pptx": ArtifactType.PPT,
    "powerpoint": ArtifactType.PPT,
    "excel": ArtifactType.EXCEL,
    "xlsx": ArtifactType.EXCEL,
    "xlsm": ArtifactType.EXCEL,
    "word": ArtifactType.WORD,
    "docx": ArtifactType.WORD,
    "doc": ArtifactType.WORD,
}

_BLOCK_ALIASES = {
    "paragraph": BlockType.TEXT,
    "para": BlockType.TEXT,
    "body": BlockType.TEXT,
    "bullets": BlockType.LIST,
    "bullet": BlockType.LIST,
    "items": BlockType.LIST,
}

_HEADING_ALIAS = {
    "h1": 1,
    "h2": 2,
    "h3": 3,
    "h4": 4,
    "h5": 5,
    "h6": 6,
}

WRITE_EXTENSIONS = {
    ArtifactType.PDF: ".pdf",
    ArtifactType.PPT: ".pptx",
    ArtifactType.EXCEL: ".xlsx",
    ArtifactType.WORD: ".docx",
}


@dataclass
class SpecBlock:
    type: BlockType = BlockType.TEXT
    text: str = ""
    table: list[list[str]] | None = None
    level: int | None = None
    block_id: str = ""
    items: list[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    location: SourceLocation | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.type.value, "text": self.text}
        if self.table is not None:
            payload["table"] = self.table
        if self.level is not None:
            payload["level"] = self.level
        if self.block_id:
            payload["block_id"] = self.block_id
        if self.items:
            payload["items"] = list(self.items)
        if self.extra:
            payload["extra"] = dict(self.extra)
        if self.location is not None:
            loc = self.location.to_dict()
            if loc:
                payload["location"] = loc
        return payload


@dataclass
class SpecSlide:
    blocks: list[SpecBlock] = field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"blocks": [block.to_dict() for block in self.blocks]}
        if self.notes:
            payload["notes"] = self.notes
        return payload


@dataclass
class SpecSheet:
    name: str = "Sheet1"
    rows: list[list[str]] = field(default_factory=list)
    cells: dict[str, Any] = field(default_factory=dict)
    block_id: str = ""
    hidden: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "rows": [list(row) for row in self.rows]}
        if self.cells:
            payload["cells"] = dict(self.cells)
        if self.block_id:
            payload["block_id"] = self.block_id
        if self.hidden:
            payload["hidden"] = True
        return payload


@dataclass
class ArtifactSpec:
    artifact_type: ArtifactType = ArtifactType.WORD
    filename: str | None = None
    title: str | None = None
    author: str | None = None
    blocks: list[SpecBlock] = field(default_factory=list)
    slides: list[SpecSlide] | None = None
    sheets: list[SpecSheet] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "artifact_type": self.artifact_type.value,
            "filename": self.filename,
            "title": self.title,
            "author": self.author,
            "blocks": [block.to_dict() for block in self.blocks],
        }
        if self.slides is not None:
            payload["slides"] = [slide.to_dict() for slide in self.slides]
        if self.sheets is not None:
            payload["sheets"] = [sheet.to_dict() for sheet in self.sheets]
        return payload

    def suffix(self) -> str:
        if self.filename:
            ext = Path(self.filename).suffix.lower()
            if ext:
                return ext
        return WRITE_EXTENSIONS[self.artifact_type]


@dataclass
class PatchOp:
    op: str
    block_id: str | None = None
    after_block_id: str | None = None
    location: SourceLocation | None = None
    text: str | None = None
    table: list[list[str]] | None = None
    sheet: str | None = None
    cell_range: str | None = None
    row: int | None = None
    col: int | None = None
    value: Any = None
    block: SpecBlock | None = None
    slide: SpecSlide | None = None
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"op": self.op}
        for key, value in asdict(self).items():
            if key == "op" or value is None or value == "" or value == []:
                continue
            if key == "location" and isinstance(self.location, SourceLocation):
                loc = self.location.to_dict()
                if loc:
                    payload["location"] = loc
                continue
            if key == "block" and self.block is not None:
                payload["block"] = self.block.to_dict()
                continue
            if key == "slide" and self.slide is not None:
                payload["slide"] = self.slide.to_dict()
                continue
            payload[key] = value
        return payload


def coerce_artifact_type(value: ArtifactType | str | None, filename: str | None = None) -> ArtifactType:
    if isinstance(value, ArtifactType):
        resolved = value
    elif value:
        key = str(value).strip().lower().lstrip(".")
        resolved = _TYPE_ALIASES.get(key)
        if resolved is None:
            try:
                resolved = ArtifactType(key)
            except ValueError as exc:
                raise UnsupportedArtifact(
                    f"Unknown artifact type {value!r}. Expected pdf, ppt, excel, or word."
                ) from exc
    elif filename:
        from .classifier import EXTENSION_MAP

        resolved = EXTENSION_MAP.get(Path(filename).suffix.lower())
        if resolved is None:
            raise ArtifactWriteError(f"Cannot infer artifact type from filename {filename!r}.")
    else:
        raise ArtifactWriteError("ArtifactSpec requires artifact_type or filename.")

    allowed = PARSEABLE_EXTENSIONS[resolved]
    if filename:
        ext = Path(filename).suffix.lower()
        if ext and ext not in allowed:
            raise UnsupportedArtifact(
                f"{filename} is not a writable {resolved.value} extension. Use {sorted(allowed)}."
            )
    return resolved


def coerce_block_type(value: BlockType | str | None) -> tuple[BlockType, int | None]:
    if isinstance(value, BlockType):
        return value, None
    if not value:
        return BlockType.TEXT, None
    key = str(value).strip().lower()
    if key in _HEADING_ALIAS:
        return BlockType.HEADING, _HEADING_ALIAS[key]
    if key in _BLOCK_ALIASES:
        return _BLOCK_ALIASES[key], None
    try:
        return BlockType(key), None
    except ValueError as exc:
        raise ArtifactWriteError(
            f"Unknown block type {value!r}. Expected heading, text, list, table, note, image, chart, ocr."
        ) from exc


def coerce_spec(spec: ArtifactSpec | dict[str, Any]) -> ArtifactSpec:
    if isinstance(spec, ArtifactSpec):
        normalize_spec(spec)
        return spec
    if not isinstance(spec, dict):
        raise ArtifactWriteError("create() expects an ArtifactSpec or a JSON object.")
    filename = spec.get("filename")
    artifact_type = coerce_artifact_type(spec.get("artifact_type") or spec.get("type"), filename)
    blocks = [coerce_block(item) for item in spec.get("blocks") or []]
    slides = None
    if spec.get("slides") is not None:
        slides = [coerce_slide(item) for item in spec["slides"]]
    sheets = None
    if spec.get("sheets") is not None:
        sheets = [coerce_sheet(item) for item in spec["sheets"]]
    result = ArtifactSpec(
        artifact_type=artifact_type,
        filename=filename,
        title=_opt_str(spec.get("title")),
        author=_opt_str(spec.get("author")),
        blocks=blocks,
        slides=slides,
        sheets=sheets,
    )
    normalize_spec(result)
    return result


def coerce_slide(value: SpecSlide | dict[str, Any]) -> SpecSlide:
    if isinstance(value, SpecSlide):
        return value
    if not isinstance(value, dict):
        raise ArtifactWriteError("Each slide must be an object with blocks.")
    return SpecSlide(
        blocks=[coerce_block(item) for item in value.get("blocks") or []],
        notes=_opt_str(value.get("notes")),
    )


def coerce_sheet(value: SpecSheet | dict[str, Any]) -> SpecSheet:
    if isinstance(value, SpecSheet):
        return value
    if not isinstance(value, dict):
        raise ArtifactWriteError("Each sheet must be an object with name/rows.")
    rows = value.get("rows") or value.get("table") or []
    return SpecSheet(
        name=str(value.get("name") or "Sheet1"),
        rows=_coerce_table(rows) or [],
        cells=dict(value.get("cells") or {}),
        block_id=str(value.get("block_id") or ""),
        hidden=bool(value.get("hidden") or False),
    )


def coerce_block(value: SpecBlock | dict[str, Any]) -> SpecBlock:
    if isinstance(value, SpecBlock):
        return value
    if not isinstance(value, dict):
        raise ArtifactWriteError("Each block must be an object.")
    block_type, alias_level = coerce_block_type(value.get("type") or value.get("block_type"))
    level = value.get("level")
    if level is None:
        level = alias_level
    elif level is not None:
        level = int(level)
    table = _coerce_table(value.get("table"))
    items = value.get("items")
    if items is not None:
        items = [str(item) for item in items]
    text = value.get("text")
    if text is None:
        text = ""
    location = value.get("location")
    if isinstance(location, dict):
        location = _location_from_dict(location)
    elif location is not None and not isinstance(location, SourceLocation):
        location = None
    return SpecBlock(
        type=block_type,
        text=str(text),
        table=table,
        level=level,
        block_id=str(value.get("block_id") or value.get("id") or ""),
        items=items,
        extra=dict(value.get("extra") or {}),
        location=location,
    )


def coerce_ops(ops: Iterable[PatchOp | dict[str, Any]]) -> list[PatchOp]:
    if ops is None:
        raise ArtifactPatchError("update() requires a list of patch ops.")
    return [coerce_op(op) for op in ops]


def coerce_op(value: PatchOp | dict[str, Any]) -> PatchOp:
    if isinstance(value, PatchOp):
        _require_known_op(value.op)
        return value
    if not isinstance(value, dict):
        raise ArtifactPatchError("Each patch op must be an object.")
    op_name = value.get("op") or value.get("operation")
    if not op_name:
        raise ArtifactPatchError("Patch op is missing 'op'.")
    op_name = str(op_name).strip()
    _require_known_op(op_name)
    location = value.get("location")
    if isinstance(location, dict):
        location = _location_from_dict(location)
    elif location is not None and not isinstance(location, SourceLocation):
        location = None
    block = value.get("block")
    if block is not None:
        block = coerce_block(block)
    slide = value.get("slide")
    if slide is not None:
        slide = coerce_slide(slide)
    table = _coerce_table(value.get("table"))
    return PatchOp(
        op=op_name,
        block_id=_opt_str(value.get("block_id") or value.get("id")),
        after_block_id=_opt_str(value.get("after_block_id")),
        location=location,
        text=None if value.get("text") is None else str(value.get("text")),
        table=table,
        sheet=_opt_str(value.get("sheet")),
        cell_range=_opt_str(value.get("cell_range") or value.get("cell")),
        row=_opt_int(value.get("row")),
        col=_opt_int(value.get("col") or value.get("column")),
        value=value.get("value"),
        block=block,
        slide=slide,
        title=_opt_str(value.get("title")),
    )


def normalize_spec(spec: ArtifactSpec) -> ArtifactSpec:
    if spec.artifact_type == ArtifactType.PPT and not spec.slides:
        spec.slides = _blocks_to_slides(spec)
    if spec.artifact_type == ArtifactType.EXCEL and not spec.sheets:
        spec.sheets = _blocks_to_sheets(spec)
        if not spec.sheets:
            spec.sheets = [SpecSheet(name="Sheet1", rows=[])]
    return spec


def list_items(block: SpecBlock) -> list[str]:
    if block.items:
        return [str(item).strip() for item in block.items if str(item).strip()]
    if block.text.strip():
        return [line.strip() for line in block.text.splitlines() if line.strip()]
    return []


def table_as_text(table: list[list[str]] | None) -> str:
    if not table:
        return ""
    return "\n".join(" | ".join(str(cell) for cell in row) for row in table)


def _require_known_op(op_name: str) -> None:
    if op_name not in PATCH_OPS:
        known = ", ".join(sorted(PATCH_OPS))
        raise ArtifactPatchError(f"Unknown patch op {op_name!r}. Expected one of: {known}.")


def _blocks_to_slides(spec: ArtifactSpec) -> list[SpecSlide]:
    slides: list[SpecSlide] = []
    current = SpecSlide()
    for block in spec.blocks:
        if block.type == BlockType.NOTE:
            current.notes = block.text
            continue
        if block.type == BlockType.HEADING and current.blocks:
            slides.append(current)
            current = SpecSlide(blocks=[block])
            continue
        current.blocks.append(block)
    if current.blocks or current.notes:
        slides.append(current)
    if spec.title and not slides:
        slides.append(SpecSlide(blocks=[SpecBlock(type=BlockType.HEADING, text=spec.title, level=1)]))
    return slides or [SpecSlide()]


def _blocks_to_sheets(spec: ArtifactSpec) -> list[SpecSheet]:
    sheets: list[SpecSheet] = []
    for index, block in enumerate(spec.blocks):
        name = str((block.extra or {}).get("sheet") or f"Sheet{index + 1}")
        rows = block.table
        if not rows and block.text.strip():
            rows = [[line] for line in block.text.splitlines() if line.strip()]
        sheets.append(
            SpecSheet(
                name=name,
                rows=[list(row) for row in (rows or [])],
                block_id=block.block_id,
            )
        )
    return sheets


def _coerce_table(value: Any) -> list[list[str]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ArtifactWriteError("table must be a 2D list of strings.")
    rows: list[list[str]] = []
    for row in value:
        if not isinstance(row, list):
            raise ArtifactWriteError("Each table row must be a list of cells.")
        rows.append(["" if cell is None else str(cell) for cell in row])
    return rows


def _location_from_dict(payload: dict[str, Any]) -> SourceLocation:
    allowed = {item.name for item in fields(SourceLocation)}
    kwargs = {key: value for key, value in payload.items() if key in allowed}
    bbox = kwargs.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        kwargs["bbox"] = tuple(float(item) for item in bbox)
    return SourceLocation(**kwargs)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
