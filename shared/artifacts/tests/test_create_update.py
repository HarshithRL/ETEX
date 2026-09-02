from __future__ import annotations

import pytest

from shared.artifacts import ArtifactHandler, ArtifactPatchError, ArtifactType
from shared.artifacts.models import BlockType

HEADING = "Overview"
PARA1 = "We compared three vendors on cost and coverage."
PARA2 = "Scores below reflect the latest round of review."
TABLE = [
    ["Vendor", "Score"],
    ["Alpha", "9"],
    ["Beta", "7"],
]
NEW_TABLE = [
    ["Vendor", "Score"],
    ["Gamma", "8"],
]


def _content_blocks() -> list[dict]:
    return [
        {"type": "heading", "text": HEADING, "level": 1},
        {"type": "text", "text": PARA1},
        {"type": "text", "text": PARA2},
        {"type": "list", "items": ["Alpha leads on coverage", "Beta leads on price"]},
        {"type": "table", "table": TABLE},
    ]


def spec_for(kind: str, filename: str) -> dict:
    if kind == "ppt":
        return {
            "artifact_type": "ppt",
            "filename": filename,
            "title": "Vendor Brief",
            "slides": [
                {
                    "blocks": [
                        {"type": "heading", "text": HEADING, "level": 1},
                        {"type": "text", "text": PARA1},
                        {"type": "list", "items": ["Alpha leads on coverage", "Beta leads on price"]},
                    ]
                },
                {
                    "blocks": [
                        {"type": "heading", "text": "Vendor Scores", "level": 1},
                        {"type": "table", "table": TABLE},
                    ]
                },
            ],
        }
    if kind == "excel":
        return {
            "artifact_type": "excel",
            "filename": filename,
            "title": "Vendor Brief",
            "sheets": [{"name": "Vendors", "rows": TABLE}],
        }
    return {
        "artifact_type": kind,
        "filename": filename,
        "title": "Vendor Brief",
        "blocks": _content_blocks(),
    }


FORMATS = [
    ("pdf", "brief.pdf", ArtifactType.PDF),
    ("ppt", "brief.pptx", ArtifactType.PPT),
    ("excel", "brief.xlsx", ArtifactType.EXCEL),
    ("word", "brief.docx", ArtifactType.WORD),
]


@pytest.fixture
def handler() -> ArtifactHandler:
    return ArtifactHandler()


@pytest.mark.parametrize("kind,filename,expected", FORMATS)
def test_create_parse_roundtrip(tmp_path, handler: ArtifactHandler, kind, filename, expected):
    dest = tmp_path / filename
    doc = handler.create(spec_for(kind, filename), dest=dest)
    assert dest.is_file()
    assert handler.classify(dest) == expected
    assert doc.artifact_type == expected
    assert doc.source == str(dest)
    joined = "\n".join(block.text for block in doc.blocks)
    tables = doc.tables()
    assert tables, f"{kind} create/parse lost tables"
    header = tables[0].table[0]
    assert "Vendor" in header
    assert "Score" in header
    body_rows = [row[0] for row in tables[0].table[1:]]
    assert "Alpha" in body_rows
    if kind == "excel":
        assert "Alpha" in joined or "Vendor" in joined
    else:
        assert HEADING in joined
        assert "three vendors" in joined or "Alpha leads" in joined
    ids = [block.block_id for block in doc.blocks]
    assert all(item.startswith("b_") for item in ids)
    assert len(ids) == len(set(ids))
    if kind in {"word", "pdf"}:
        assert any(block.type == BlockType.HEADING and HEADING in block.text for block in doc.blocks)


@pytest.mark.parametrize("kind,filename,expected", [item for item in FORMATS if item[0] != "excel"])
def test_update_replace_text(tmp_path, handler: ArtifactHandler, kind, filename, expected):
    dest = tmp_path / filename
    doc = handler.create(spec_for(kind, filename), dest=dest)
    target = next(block for block in doc.blocks if HEADING in block.text)
    updated = handler.update(
        dest,
        [{"op": "replace_text", "block_id": target.block_id, "text": "Executive Summary"}],
    )
    joined = "\n".join(block.text for block in updated.blocks)
    assert "Executive Summary" in joined
    assert not any(block.text.strip() == HEADING for block in updated.blocks)


def test_update_replace_table_word_pdf_ppt(tmp_path, handler: ArtifactHandler):
    for kind, filename, _expected in FORMATS:
        if kind == "excel":
            continue
        dest = tmp_path / filename
        doc = handler.create(spec_for(kind, filename), dest=dest)
        table_block = doc.tables()[0]
        updated = handler.update(
            dest,
            [{"op": "replace_table", "block_id": table_block.block_id, "table": NEW_TABLE}],
        )
        rows = updated.tables()[0].table
        assert rows[1][0] == "Gamma"
        assert "Alpha" not in [row[0] for row in rows[1:]]


def test_update_set_cell_and_replace_table_excel(tmp_path, handler: ArtifactHandler):
    dest = tmp_path / "scores.xlsx"
    doc = handler.create(spec_for("excel", "scores.xlsx"), dest=dest)
    patched = handler.update(
        dest,
        [{"op": "set_cell", "sheet": "Vendors", "cell_range": "B2", "value": "10"}],
    )
    table = patched.tables()[0].table
    assert table[1][0] == "Alpha"
    assert table[1][1] in {"10", "10.0"}
    table_block = patched.tables()[0]
    replaced = handler.update(
        dest,
        [{"op": "replace_table", "block_id": table_block.block_id, "table": NEW_TABLE}],
    )
    assert replaced.tables()[0].table[1][0] == "Gamma"


def test_invalid_op_raises(tmp_path, handler: ArtifactHandler):
    dest = tmp_path / "brief.docx"
    handler.create(spec_for("word", "brief.docx"), dest=dest)
    with pytest.raises(ArtifactPatchError, match="Unknown patch op"):
        handler.update(dest, [{"op": "explode_block", "block_id": "b_nope"}])


def test_missing_block_id_raises(tmp_path, handler: ArtifactHandler):
    dest = tmp_path / "brief.docx"
    handler.create(spec_for("word", "brief.docx"), dest=dest)
    with pytest.raises(ArtifactPatchError, match="block_id"):
        handler.update(dest, [{"op": "replace_text", "text": "no target"}])


def test_unknown_block_id_raises(tmp_path, handler: ArtifactHandler):
    dest = tmp_path / "brief.docx"
    handler.create(spec_for("word", "brief.docx"), dest=dest)
    with pytest.raises(ArtifactPatchError, match="No block with id"):
        handler.update(dest, [{"op": "replace_text", "block_id": "b_missing", "text": "x"}])


def test_create_exports_and_source_path(tmp_path, handler: ArtifactHandler):
    dest = tmp_path / "note.docx"
    doc = handler.create(
        {
            "artifact_type": "word",
            "filename": "note.docx",
            "blocks": [{"type": "text", "text": "hello world"}],
        },
        dest=dest,
    )
    assert dest.is_file()
    assert "hello world" in doc.plain_text()
    from shared.artifacts import ArtifactSpec, PatchOp

    assert ArtifactSpec and PatchOp
