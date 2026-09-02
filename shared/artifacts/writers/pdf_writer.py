from __future__ import annotations

"""Simple multi-page PDF report writer (reportlab).

Tuned so the EXISTING parser recovers headings, lists, and tables:
- Headings: Helvetica-Bold 22/16pt, short titles, no trailing punctuation
- Body: Helvetica 10pt (keeps heading-size cut below heading fonts)
- Lists: literal '• ' prefix so pdf_headings._LIST_RE matches
- Tables: ruled GRID with >=2 columns so pymupdf.find_tables sees them
"""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..exceptions import ArtifactWriteError
from ..models import ArtifactType, BlockType
from ..spec import ArtifactSpec, SpecBlock, list_items

# Parser heading_level() uses cut = max(11, median_body * 1.28).
# Body at 10pt with several lines keeps cut ~12.8; 22pt headings stay headings.
_H1_SIZE = 22
_H2_SIZE = 16
_BODY_SIZE = 10


class PdfWriter:
    kind = ArtifactType.PDF

    def write(self, spec: ArtifactSpec, dest: Path) -> None:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(
                str(dest),
                pagesize=LETTER,
                title=spec.title or "",
                author=spec.author or "",
                leftMargin=0.9 * inch,
                rightMargin=0.9 * inch,
                topMargin=0.85 * inch,
                bottomMargin=0.85 * inch,
            )
            styles = _styles()
            story: list = []
            blocks = list(spec.blocks)
            if not blocks and spec.title:
                blocks = [SpecBlock(type=BlockType.HEADING, text=spec.title, level=1)]
            for block in blocks:
                story.extend(_flowables(block, styles))
            if not story:
                story.append(Paragraph(escape(spec.title or "Untitled"), styles["h1"]))
            doc.build(story)
        except ArtifactWriteError:
            raise
        except Exception as exc:
            raise ArtifactWriteError(f"Failed to write PDF {dest.name}: {exc}") from exc


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "h1": ParagraphStyle(
            "MateH1",
            fontName="Helvetica-Bold",
            fontSize=_H1_SIZE,
            leading=_H1_SIZE + 4,
            spaceBefore=10,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "h2": ParagraphStyle(
            "MateH2",
            fontName="Helvetica-Bold",
            fontSize=_H2_SIZE,
            leading=_H2_SIZE + 4,
            spaceBefore=8,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "body": ParagraphStyle(
            "MateBody",
            fontName="Helvetica",
            fontSize=_BODY_SIZE,
            leading=_BODY_SIZE + 4,
            spaceBefore=0,
            spaceAfter=8,
            alignment=TA_LEFT,
        ),
        "list": ParagraphStyle(
            "MateList",
            fontName="Helvetica",
            fontSize=_BODY_SIZE,
            leading=_BODY_SIZE + 4,
            leftIndent=12,
            spaceBefore=0,
            spaceAfter=2,
            alignment=TA_LEFT,
        ),
        "cell": ParagraphStyle(
            "MateCell",
            fontName="Helvetica",
            fontSize=_BODY_SIZE,
            leading=_BODY_SIZE + 2,
            alignment=TA_LEFT,
        ),
        "cell_header": ParagraphStyle(
            "MateCellHeader",
            fontName="Helvetica-Bold",
            fontSize=_BODY_SIZE,
            leading=_BODY_SIZE + 2,
            alignment=TA_LEFT,
        ),
    }


def _flowables(block: SpecBlock, styles: dict[str, ParagraphStyle]) -> list:
    if block.type == BlockType.HEADING:
        text = _one_line(block.text)
        if not text:
            return []
        style = styles["h1"] if (block.level or 1) <= 1 else styles["h2"]
        return [Paragraph(escape(text), style), Spacer(1, 4)]
    if block.type == BlockType.LIST:
        items = list_items(block)
        if not items:
            return []
        return [Paragraph(escape(f"• {item}"), styles["list"]) for item in items] + [Spacer(1, 6)]
    if block.type == BlockType.TABLE:
        rows = block.table or []
        if len(rows) < 2 or max(len(row) for row in rows) < 2:
            # Parser only accepts tables with >=2 rows and >=2 columns.
            # Fall back to body text so the content is not dropped.
            text = " | ".join(" | ".join(row) for row in rows) if rows else ""
            return [Paragraph(escape(text), styles["body"])] if text else []
        return [_table(rows, styles), Spacer(1, 10)]
    text = (block.text or "").strip()
    if not text:
        return []
    parts = [Paragraph(escape(line), styles["body"]) for line in text.splitlines() if line.strip()]
    return parts or []


def _table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> KeepTogether:
    width = max(len(row) for row in rows)
    padded = [list(row) + [""] * (width - len(row)) for row in rows]
    data = []
    for r_i, row in enumerate(padded):
        style = styles["cell_header"] if r_i == 0 else styles["cell"]
        data.append([Paragraph(escape(cell), style) for cell in row])
    usable = 6.7 * inch
    col_w = usable / width
    table = Table(data, colWidths=[col_w] * width, repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
                ("BOX", (0, 0), (-1, -1), 1.0, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2EC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return KeepTogether(table)


def _one_line(text: str) -> str:
    return " ".join((text or "").split()).strip()
