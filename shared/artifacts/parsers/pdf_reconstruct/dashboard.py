from __future__ import annotations

from ...blocks import make_content_block
from ...models import BlockType, ContentBlock, SourceLocation
from ..pdf_geometry import contained_in, overlap_ratio, round_bbox, union_bbox
from ..pdf_layout import LayoutLine
from ..pdf_tables import PdfTableExtractor, table_to_text
from ..pdf_visuals import extract_visuals
from .base import ReconstructPage, lines_outside_tables, stamp_blocks


def cluster_tiles(
    lines: list[LayoutLine],
    page: object | None = None,
    page_width: float = 0.0,
    page_height: float = 0.0,
) -> list[list[LayoutLine]]:
    if not lines:
        return []
    assigned: dict[int, int] = {}
    tiles: list[list[LayoutLine]] = []
    boxes = _tile_boxes_from_drawings(page, page_width, page_height) if page is not None else []
    for line in lines:
        box_index = _containing_tile(line, boxes)
        if box_index is None:
            continue
        while len(tiles) <= box_index:
            tiles.append([])
        tiles[box_index].append(line)
        assigned[id(line)] = box_index
    leftover = [line for line in lines if id(line) not in assigned]
    tiles.extend(_proximity_clusters(leftover))
    return [group for group in tiles if group]


def tile_text(lines: list[LayoutLine]) -> str:
    ordered = sorted(lines, key=lambda line: (round(line.bbox[1] / 4), line.bbox[0]))
    parts: list[str] = []
    index = 0
    while index < len(ordered):
        current = ordered[index]
        if index + 1 < len(ordered):
            nxt = ordered[index + 1]
            if _is_label(current.text) and _is_value(nxt.text):
                parts.append(f"{current.text.strip()} {nxt.text.strip()}")
                index += 2
                continue
            if _is_value(current.text) and _is_label(nxt.text) and _same_row(current, nxt):
                parts.append(f"{nxt.text.strip()} {current.text.strip()}")
                index += 2
                continue
        parts.append(current.text.strip())
        index += 1
    return " ".join(part for part in parts if part)


class DashboardReconstructor:
    name = "dashboard"

    def reconstruct(
        self, ctx: ReconstructPage, start_index: int
    ) -> tuple[int, list[ContentBlock]]:
        index = start_index
        tables: list[tuple[list[list[str]], tuple[float, float, float, float], str]] = []
        if ctx.options.include_tables:
            for matrix, bbox, engine in PdfTableExtractor().extract(
                ctx.page, ctx.path, ctx.page_index, ctx.kind, ctx.options.password
            ):
                if len(matrix) >= 3 and max(len(row) for row in matrix) >= 3:
                    tables.append((matrix, bbox, engine))
        table_boxes = [bbox for _, bbox, _ in tables]
        leftover = lines_outside_tables(ctx.lines, table_boxes)

        blocks: list[ContentBlock] = []
        for table_i, (matrix, bbox, engine) in enumerate(tables):
            index += 1
            blocks.append(
                make_content_block(
                    seq_id=f"pdf-{index:04d}",
                    block_type=BlockType.TABLE,
                    text=table_to_text(matrix),
                    table=matrix,
                    location=SourceLocation(
                        page=ctx.page_no,
                        bbox=round_bbox(bbox),
                        page_width=ctx.width,
                        page_height=ctx.height,
                        table_index=table_i,
                    ),
                    extra={
                        "engine": engine,
                        "page_kind": ctx.kind,
                        "reconstructor": self.name,
                    },
                )
            )

        index, visual_blocks = extract_visuals(
            ctx.page, leftover, "dashboard", ctx.page_no, table_boxes, index
        )
        blocks.extend(visual_blocks)

        for group in cluster_tiles(leftover, ctx.page, ctx.width, ctx.height):
            text = tile_text(group)
            if not text:
                continue
            index += 1
            blocks.append(
                make_content_block(
                    seq_id=f"pdf-{index:04d}",
                    block_type=BlockType.TEXT,
                    text=text,
                    location=SourceLocation(
                        page=ctx.page_no,
                        bbox=round_bbox(union_bbox([item.bbox for item in group])),
                        page_width=ctx.width,
                        page_height=ctx.height,
                    ),
                    extra={
                        "engine": "pymupdf",
                        "page_kind": ctx.kind,
                        "reconstructor": self.name,
                        "role": "kpi",
                    },
                )
            )
        stamp_blocks(blocks, reconstructor=self.name, page_kind=ctx.kind)
        blocks.sort(key=_yx)
        return index, blocks


def _yx(block: ContentBlock) -> tuple[float, float]:
    bbox = block.location.bbox
    if bbox is None:
        return (10_000.0, 0.0)
    return (bbox[1], bbox[0])


def _is_label(text: str) -> bool:
    stripped = text.strip()
    if not stripped or _is_value(stripped):
        return False
    return len(stripped) <= 48 and not stripped.endswith((".", ",", ";"))


def _is_value(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if any(ch in stripped for ch in "€$£%"):
        return True
    digits = sum(ch.isdigit() for ch in stripped)
    return digits >= 1 and digits >= max(1, len(stripped) // 3)


def _same_row(a: LayoutLine, b: LayoutLine) -> bool:
    ay = (a.bbox[1] + a.bbox[3]) / 2
    by = (b.bbox[1] + b.bbox[3]) / 2
    return abs(ay - by) < max(a.font_size, b.font_size, 10.0) * 1.2


def _tile_boxes_from_drawings(
    page: object, page_width: float, page_height: float
) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []
    try:
        drawings = page.get_drawings()  # type: ignore[attr-defined]
    except Exception:
        return boxes
    for drawing in drawings:
        rect = drawing.get("rect")
        if rect is None:
            continue
        box = round_bbox((float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)))
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width < 50 or height < 28:
            continue
        if page_width and width > page_width * 0.7:
            continue
        if page_height and height > page_height * 0.45:
            continue
        boxes.append(box)
    return _merge_similar_boxes(boxes)


def _merge_similar_boxes(
    boxes: list[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    merged: list[tuple[float, float, float, float]] = []
    for box in boxes:
        placed = False
        for index, existing in enumerate(merged):
            if overlap_ratio(box, existing) >= 0.7:
                merged[index] = round_bbox(union_bbox([box, existing]))
                placed = True
                break
        if not placed:
            merged.append(box)
    return merged


def _containing_tile(
    line: LayoutLine, boxes: list[tuple[float, float, float, float]]
) -> int | None:
    for index, box in enumerate(boxes):
        if contained_in(line.bbox, box, padding=6.0):
            return index
    return None


def _proximity_clusters(lines: list[LayoutLine]) -> list[list[LayoutLine]]:
    remaining = list(lines)
    clusters: list[list[LayoutLine]] = []
    while remaining:
        seed = remaining.pop(0)
        cluster = [seed]
        changed = True
        while changed:
            changed = False
            keep: list[LayoutLine] = []
            for line in remaining:
                if _near_cluster(line, cluster):
                    cluster.append(line)
                    changed = True
                else:
                    keep.append(line)
            remaining = keep
        clusters.append(cluster)
    return clusters


def _near_cluster(line: LayoutLine, cluster: list[LayoutLine]) -> bool:
    for member in cluster:
        v_gap = max(0.0, line.bbox[1] - member.bbox[3], member.bbox[1] - line.bbox[3])
        h_gap = max(0.0, line.bbox[0] - member.bbox[2], member.bbox[0] - line.bbox[2])
        v_overlap = min(line.bbox[3], member.bbox[3]) - max(line.bbox[1], member.bbox[1])
        h_overlap = min(line.bbox[2], member.bbox[2]) - max(line.bbox[0], member.bbox[0])
        if v_gap < 16 and h_overlap > -12:
            return True
        if h_gap < 40 and v_overlap > 0:
            return True
    return False
