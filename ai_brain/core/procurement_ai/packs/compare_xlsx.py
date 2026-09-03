"""Comparison workbook. Direct = France P×Q pack. Indirect = SWIFT BAFO pack. LLM fills cells."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from ai_brain.core.procurement_ai.packs import store
from ai_brain.core.procurement_ai.packs.matrix_direct import write_direct
from ai_brain.core.procurement_ai.packs.matrix_extract import (
    corpus_from_chunks,
    empty_direct,
    empty_indirect,
    extract_matrix,
)
from ai_brain.core.procurement_ai.packs.matrix_indirect import write_indirect
from ai_brain.core.procurement_ai.packs.matrix_schema import DirectMatrix, IndirectMatrix
from ai_brain.core.procurement_ai.packs.xlsx_style import COVER_FIELDS, autosize, header_row
from ai_brain.core.procurement_ai.process_type import DIRECT_TG
from shared.logger_global import get_logger

log = get_logger(__name__, service="ai_brain")


def build_comparison_xlsx(
    project_id: str,
    insights: dict[str, Any],
    *,
    thread_id: str = "",
    chunks: list[Any] | None = None,
    artifacts: list[Any] | None = None,
) -> dict[str, Any]:
    store.write_status(project_id, "xlsx", status="running", thread_id=thread_id or None)
    filename = "comparison_matrix.xlsx"
    path = store.pack_file(project_id, filename)
    source_text = corpus_from_chunks(chunks or [], artifacts or [])
    extracted = extract_matrix(
        insights,
        source_text,
        chunks=chunks or [],
        artifacts=artifacts or [],
    )
    llm_used = extracted is not None
    process = insights.get("process_type") or ""
    wb = Workbook()
    cover = wb.active
    cover.title = "Cover"
    _write_cover(cover, insights, llm_used=llm_used)
    _write_vendors(wb.create_sheet("Vendors"), insights)
    if process == DIRECT_TG:
        matrix = extracted if isinstance(extracted, DirectMatrix) else empty_direct(insights)
        write_direct(wb, insights, matrix)
    else:
        matrix = extracted if isinstance(extracted, IndirectMatrix) else empty_indirect(insights)
        write_indirect(wb, insights, matrix)
    _write_field_map(wb.create_sheet("FieldMap"))
    wb.save(path)
    href = store.flask_href(project_id, "xlsx")
    store.write_status(
        project_id,
        "xlsx",
        status="ready",
        href=href,
        filename=filename,
        thread_id=thread_id or None,
        error=None,
    )
    log.info(
        "comparison xlsx ready project_id={} process={} llm_used={} sheets={}",
        project_id,
        process or "unset",
        llm_used,
        wb.sheetnames,
    )
    return {
        "status": "ready",
        "href": href,
        "filename": filename,
        "path": str(path),
        "llm_used": llm_used,
        "sheets": list(wb.sheetnames),
    }


def _write_cover(ws, insights: dict[str, Any], *, llm_used: bool) -> None:
    ws["A1"] = "Mate comparison pack"
    ws["A1"].font = Font(bold=True, size=16, color="FF6900")
    ws["A2"] = (
        "Draft workbook. Humans award. Empty is missing, never zero. "
        f"Cells filled by LangChain structured extract: {'yes' if llm_used else 'no (template only)'}."
    )
    ws["A4"] = "Named field"
    ws["B4"] = "Value"
    ws["A4"].font = Font(bold=True)
    ws["B4"].font = Font(bold=True)
    for row, (field, key) in enumerate(COVER_FIELDS, start=5):
        ws[f"A{row}"] = field
        ws[f"B{row}"] = insights.get(key, "")
    ws["A12"] = "FIELD_DECISION_SUMMARY"
    ws["B12"] = (insights.get("decision") or {}).get("summary") or ""
    ws["A13"] = "FIELD_WEIGHTS_LOCKED"
    ws["B13"] = "NO — draft scores only"
    ws["A14"] = "FIELD_AWARD"
    ws["B14"] = "Not awarded"
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 72


def _write_vendors(ws, insights: dict[str, Any]) -> None:
    header_row(ws, ["Vendor", "Role", "Files", "Coverage %", "Headline", "Evidence locator"])
    vendors = insights.get("vendors") or []
    if not vendors:
        ws["A2"] = "No vendor column yet"
        return
    for index, vendor in enumerate(vendors, start=2):
        evidence = vendor.get("evidence") or []
        ws[f"A{index}"] = vendor.get("name")
        ws[f"B{index}"] = vendor.get("role")
        ws[f"C{index}"] = vendor.get("artifact_count")
        ws[f"D{index}"] = vendor.get("coverage_pct")
        ws[f"E{index}"] = vendor.get("headline")
        ws[f"F{index}"] = evidence[0].get("locator") if evidence else "missing"
    autosize(ws)


def _write_field_map(ws) -> None:
    header_row(ws, ["PPT field", "Excel sheet", "Cell / column"])
    rows = [
        ("FIELD_PROCESS_LABEL", "Cover", "B6"),
        ("FIELD_OWNER_ENTITY", "Cover", "B7"),
        ("FIELD_PROJECT_CODE", "Cover", "B8"),
        ("FIELD_PROJECT_NAME", "Cover", "B9"),
        ("FIELD_KNOWLEDGE_PCT", "Cover", "B10"),
        ("FIELD_DECISION_SUMMARY", "Cover", "B12"),
        ("FIELD_WEIGHTS_LOCKED", "Cover", "B13"),
        ("FIELD_AWARD", "Cover", "B14"),
        ("FIELD_VENDOR_NAME", "Vendors", "A"),
        ("FIELD_VENDOR_HEADLINE", "Vendors", "E"),
        ("FIELD_TCO", "Final BAFO Comparison", "row Total TCO year 1"),
    ]
    for index, row in enumerate(rows, start=2):
        ws[f"A{index}"] = row[0]
        ws[f"B{index}"] = row[1]
        ws[f"C{index}"] = row[2]
    autosize(ws)


def existing_xlsx_path(project_id: str) -> Path | None:
    status = store.read_status(project_id).get("xlsx") or {}
    filename = status.get("filename")
    if not filename:
        return None
    path = store.pack_file(project_id, filename)
    return path if path.exists() else None
