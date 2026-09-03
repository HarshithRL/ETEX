from __future__ import annotations

from shared.artifacts.blocks import make_content_block
from shared.artifacts.chunking import ChunkOptions, chunk_document, estimate_tokens
from shared.artifacts.models import (
    ArtifactDocument,
    ArtifactMetadata,
    ArtifactType,
    BlockType,
    SourceLocation,
)

_TIGHT = ChunkOptions(target_tokens=80, max_tokens=120)


def _document(blocks, filename: str = "Vendor_A.pdf") -> ArtifactDocument:
    return ArtifactDocument(
        source=filename,
        artifact_type=ArtifactType.PDF,
        metadata=ArtifactMetadata(filename=filename, artifact_type=ArtifactType.PDF),
        blocks=list(blocks),
    )


def test_packs_same_heading_path_and_splits_on_change():
    blocks = [
        make_content_block(
            seq_id="pdf-0001",
            block_type=BlockType.TEXT,
            text="Net 30 payment terms apply to all invoices.",
            location=SourceLocation(page=1),
            heading_path=["Pricing", "Payment terms"],
        ),
        make_content_block(
            seq_id="pdf-0002",
            block_type=BlockType.TEXT,
            text="Late fees accrue at 1.5 percent per month.",
            location=SourceLocation(page=1),
            heading_path=["Pricing", "Payment terms"],
        ),
        make_content_block(
            seq_id="pdf-0003",
            block_type=BlockType.TEXT,
            text="Warranty covers defects for twelve months.",
            location=SourceLocation(page=2),
            heading_path=["Warranty"],
        ),
    ]
    chunks = chunk_document(_document(blocks), _TIGHT)
    assert len(chunks) == 2
    assert chunks[0].heading_path == ["Pricing", "Payment terms"]
    assert chunks[0].text.startswith("[Vendor_A.pdf] Pricing > Payment terms")
    assert "Net 30" in chunks[0].text
    assert "Late fees" in chunks[0].text
    assert chunks[1].heading_path == ["Warranty"]
    assert chunks[0].location["page"] == 1
    assert chunks[1].location["page"] == 2


def test_spans_pdf_pages_under_same_heading():
    blocks = [
        make_content_block(
            seq_id="pdf-0001",
            block_type=BlockType.TEXT,
            text="Section continues from page one.",
            location=SourceLocation(page=3, bbox=(10.0, 20.0, 100.0, 40.0)),
            heading_path=["Scope"],
        ),
        make_content_block(
            seq_id="pdf-0002",
            block_type=BlockType.TEXT,
            text="And finishes on page two of the section.",
            location=SourceLocation(page=4, bbox=(10.0, 50.0, 100.0, 80.0)),
            heading_path=["Scope"],
        ),
    ]
    chunks = chunk_document(_document(blocks), _TIGHT)
    assert len(chunks) == 1
    assert chunks[0].location["page"] == 3
    assert chunks[0].location["page_end"] == 4
    assert "bbox" not in chunks[0].location


def test_isolates_slides_even_with_same_heading_path():
    blocks = [
        make_content_block(
            seq_id="ppt-0001",
            block_type=BlockType.TEXT,
            text="Agenda for the kickoff.",
            location=SourceLocation(slide=1),
            heading_path=["Kickoff"],
        ),
        make_content_block(
            seq_id="ppt-0002",
            block_type=BlockType.TEXT,
            text="Timeline for delivery.",
            location=SourceLocation(slide=2),
            heading_path=["Kickoff"],
        ),
    ]
    chunks = chunk_document(
        _document(blocks, filename="Deck.pptx"),
        _TIGHT,
    )
    assert len(chunks) == 2
    assert chunks[0].location["slide"] == 1
    assert chunks[1].location["slide"] == 2


def test_isolates_sheets():
    blocks = [
        make_content_block(
            seq_id="excel-0001",
            block_type=BlockType.TABLE,
            text="Item | Price",
            table=[["Item", "Price"], ["Paper", "10"]],
            location=SourceLocation(sheet="Quotes", cell_range="A1:B2"),
        ),
        make_content_block(
            seq_id="excel-0002",
            block_type=BlockType.TABLE,
            text="Name | Qty",
            table=[["Name", "Qty"], ["Pens", "4"]],
            location=SourceLocation(sheet="Stock", cell_range="A1:B2"),
        ),
    ]
    chunks = chunk_document(_document(blocks, filename="Bid.xlsx"), _TIGHT)
    assert len(chunks) == 2
    assert chunks[0].chunk_type == "table"
    assert chunks[0].location["sheet"] == "Quotes"
    assert chunks[1].location["sheet"] == "Stock"
    assert chunks[0].text.startswith("[Bid.xlsx] Quotes")
    assert "| Item |" in chunks[0].text


def test_splits_oversized_table_keeping_header():
    header = ["SKU", "Description"]
    body = [[f"S{index:03d}", f"Item number {index} with extra detail"] for index in range(30)]
    block = make_content_block(
        seq_id="excel-0001",
        block_type=BlockType.TABLE,
        text="table",
        table=[header, *body],
        location=SourceLocation(sheet="Pricing", cell_range="A1:B31"),
        heading_path=["Pricing"],
    )
    chunks = chunk_document(
        _document([block], filename="Matrix.xlsx"),
        ChunkOptions(target_tokens=20, max_tokens=50),
    )
    assert len(chunks) > 1
    assert all(chunk.chunk_type == "table" for chunk in chunks)
    assert all(chunk.text.startswith("[Matrix.xlsx] Pricing") for chunk in chunks)
    assert all("| SKU |" in chunk.text for chunk in chunks)
    assert all(chunk.token_count == estimate_tokens(chunk.text) for chunk in chunks)


def test_skips_empty_and_image_placeholders():
    blocks = [
        make_content_block(
            seq_id="pdf-0001",
            block_type=BlockType.TEXT,
            text="   ",
            location=SourceLocation(page=1),
        ),
        make_content_block(
            seq_id="ppt-0001",
            block_type=BlockType.IMAGE,
            text="[image on slide 1]",
            location=SourceLocation(slide=1),
        ),
        make_content_block(
            seq_id="ppt-0002",
            block_type=BlockType.TEXT,
            text="[image]",
            location=SourceLocation(slide=1),
        ),
        make_content_block(
            seq_id="pdf-0002",
            block_type=BlockType.TEXT,
            text="The only retained paragraph.",
            location=SourceLocation(page=1),
            heading_path=["Intro"],
        ),
    ]
    chunks = chunk_document(_document(blocks), _TIGHT)
    assert len(chunks) == 1
    assert chunks[0].text.startswith("[Vendor_A.pdf] Intro")
    assert "The only retained paragraph." in chunks[0].text
    assert "[image" not in chunks[0].text


def test_to_dict_omits_chunks():
    doc = _document([])
    doc.chunks = chunk_document(doc)
    payload = doc.to_dict()
    assert "chunks" not in payload
