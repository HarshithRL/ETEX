from __future__ import annotations

from shared.artifacts.blocks import make_content_block
from shared.artifacts.citations import citation_from_block
from shared.artifacts.models import BlockType, ContentBlock, COORD_PDF_POINTS, SourceLocation
from shared.artifacts.parsers.pdf_chrome import is_header_noise
from shared.artifacts.parsers.pdf_headings import heading_level
from shared.artifacts.parsers.pdf_tables import drop_empty_columns
from shared.artifacts._markdown_convertor import LocationAnnotator


def test_heading_numbered_title_only():
    assert heading_level("2.1 Scope", font_size=12, bold=True, cut=11) == 2
    assert heading_level("3.2 Summary", font_size=10, bold=True, cut=11) == 2
    assert heading_level("3. Our offer", font_size=12, bold=True, cut=11) == 1
    assert heading_level(
        "1 Also see 3.4 Reliance on the previous assessment's conclusions.",
        font_size=14,
        bold=True,
        cut=11,
    ) is None
    assert heading_level("N.B", font_size=10, bold=True, cut=11) is None
    assert heading_level("of 10% on the daily rates.", font_size=10, bold=True, cut=11) is None


def test_heading_rejects_dates_codes_and_kpis():
    assert heading_level("8 January 1990", font_size=14, bold=True, cut=11) is None
    assert heading_level("0 ZAVENTEM", font_size=12, bold=True, cut=11) is None
    assert heading_level("ESG", font_size=16, bold=True, cut=11) is None
    assert heading_level("500 - 999", font_size=14, bold=True, cut=11) is None
    assert heading_level("€1,750,000", font_size=18, bold=True, cut=11) is None


def test_footer_noise_etex_group():
    assert is_header_noise("ETEX GROUP I 13")
    assert is_header_noise("ETEX GROUP | 13")
    assert is_header_noise("ETEX GROUP I")
    assert is_header_noise("Printed On")
    assert is_header_noise("Printed On: 12 March 2026")
    assert is_header_noise("Page 1 of 23")
    assert not is_header_noise("3.2 Summary")


def test_drop_empty_columns():
    table = [
        ["SERVICES", "", "TOTALS (€)"],
        ["Year 1", "", "35.251"],
    ]
    cleaned = drop_empty_columns(table)
    assert cleaned == [["SERVICES", "TOTALS (€)"], ["Year 1", "35.251"]]


def test_citation_from_block():
    block = make_content_block(
        seq_id="pdf-0137",
        block_type=BlockType.TABLE,
        text="Year 1 assessment (inclusive of 10% overall discount) | 35.251",
        location=SourceLocation(
            page=13,
            bbox=(70.9, 248.4, 531.7, 343.3),
            page_width=595.4,
            page_height=841.8,
        ),
        heading_path=["3. Our offer", "3.2 Summary"],
    )
    citation = citation_from_block(block, "sha256:abc", COORD_PDF_POINTS)
    assert citation["block_id"] == block.block_id
    assert citation["page"] == 13
    assert citation["bbox"] == [70.9, 248.4, 531.7, 343.3]
    assert citation["page_width"] == 595.4
    assert citation["heading_path"][-1] == "3.2 Summary"
    assert "35.251" in citation["quote"]


def test_markdown_loc_comment_shape():
    block = ContentBlock(
        id="pdf-0001",
        block_id="b_8574e45bbf58",
        type=BlockType.TABLE,
        text="SERVICES",
        location=SourceLocation(page=13),
    )
    comment = LocationAnnotator().comment(block)
    assert comment == "<!-- loc page=13 block=b_8574e45bbf58 type=table -->"
    assert "*" not in comment
    assert "filename" not in comment
