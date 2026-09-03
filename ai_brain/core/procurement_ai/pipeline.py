"""Deterministic KB + knowledge graph. No LLM. Safe to run in parallel after parse."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ai_brain.core.procurement_ai.insights import build_insight_payload
from ai_brain.core.procurement_ai.packs import store


def pipeline_path(project_id: str, name: str):
    path = store.project_root(project_id) / "pipeline"
    path.mkdir(parents=True, exist_ok=True)
    return path / name


def write_json(project_id: str, name: str, payload: dict[str, Any]) -> str:
    path = pipeline_path(project_id, name)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)


def read_json(project_id: str, name: str) -> dict[str, Any] | None:
    path = pipeline_path(project_id, name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def build_knowledge_base(project: Any, artifacts: list[Any], chunks: list[Any]) -> dict[str, Any]:
    insights = build_insight_payload(project, artifacts, chunks)
    entities = [
        {
            "type": "Project",
            "id": insights["project_id"],
            "code": insights["project_code"],
            "name": insights["project_name"],
            "process_type": insights["process_type"],
            "owner_entity": insights["owner_entity"],
        }
    ]
    for vendor in insights.get("vendors") or []:
        entities.append(
            {
                "type": "Vendor",
                "id": vendor.get("vendor_id"),
                "name": vendor.get("name"),
                "headline": vendor.get("headline"),
                "artifact_count": vendor.get("artifact_count"),
            }
        )
    for artifact in artifacts:
        entities.append(
            {
                "type": "Artifact",
                "id": getattr(artifact, "id", ""),
                "name": getattr(artifact, "original_name", ""),
                "parse_status": getattr(artifact, "parse_status", ""),
            }
        )
    for item in (insights.get("requirements") or {}).get("items") or []:
        entities.append(
            {
                "type": "Requirement",
                "id": item.get("checklist_key"),
                "label": item.get("label"),
                "status": item.get("status"),
                "severity": item.get("severity"),
            }
        )
    return {
        "status": "ready" if artifacts else "empty",
        "kind": "knowledge_base",
        "knowledge_pct": insights.get("knowledge_pct"),
        "process_type": insights.get("process_type"),
        "entities": entities,
        "missing": [
            item.get("label")
            for item in (insights.get("requirements") or {}).get("items") or []
            if item.get("status") == "missing" and item.get("severity") == "blocking"
        ],
        "insights": insights,
    }


def build_knowledge_graph(project: Any, artifacts: list[Any], chunks: list[Any]) -> dict[str, Any]:
    insights = build_insight_payload(project, artifacts, chunks)
    project_id = insights["project_id"] or "project"
    nodes = [
        {
            "id": f"project:{project_id}",
            "type": "Project",
            "label": insights["project_name"] or insights["project_code"] or "Project",
        }
    ]
    edges: list[dict[str, str]] = []
    for vendor in insights.get("vendors") or []:
        vendor_id = f"vendor:{vendor.get('vendor_id') or vendor.get('name')}"
        nodes.append({"id": vendor_id, "type": "Vendor", "label": vendor.get("name") or "Vendor"})
        edges.append({"from": f"project:{project_id}", "to": vendor_id, "rel": "has_bidder"})
    by_vendor: dict[str, str] = {}
    for vendor in insights.get("vendors") or []:
        by_vendor[str(vendor.get("name") or "")] = f"vendor:{vendor.get('vendor_id')}"
    for artifact in artifacts:
        aid = f"artifact:{getattr(artifact, 'id', '')}"
        name = getattr(artifact, "original_name", "") or "file"
        nodes.append({"id": aid, "type": "Artifact", "label": name})
        vendor_name = next(
            (
                vendor.get("name")
                for vendor in insights.get("vendors") or []
                if vendor.get("name") and vendor.get("name") in name
            ),
            None,
        )
        target = by_vendor.get(vendor_name or "", f"project:{project_id}")
        edges.append({"from": target, "to": aid, "rel": "submitted"})
    for item in (insights.get("requirements") or {}).get("items") or []:
        rid = f"req:{item.get('checklist_key')}"
        nodes.append(
            {
                "id": rid,
                "type": "Requirement",
                "label": item.get("label") or item.get("checklist_key"),
                "status": item.get("status"),
            }
        )
        edges.append({"from": f"project:{project_id}", "to": rid, "rel": "requires"})
    return {
        "status": "ready" if artifacts else "empty",
        "kind": "knowledge_graph",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


def persist_kb(project_id: str, project: Any, artifacts: list[Any], chunks: list[Any]) -> dict[str, Any]:
    payload = build_knowledge_base(project, artifacts, chunks)
    payload["path"] = write_json(project_id, "knowledge_base.json", payload)
    return payload


def persist_kg(project_id: str, project: Any, artifacts: list[Any], chunks: list[Any]) -> dict[str, Any]:
    payload = build_knowledge_graph(project, artifacts, chunks)
    payload["path"] = write_json(project_id, "knowledge_graph.json", payload)
    return payload


def run_kb_kg_parallel(project_id: str) -> dict[str, Any]:
    """Fan-out KB and graph on two workers. Call after parse has joined."""
    from ai_brain.core.procurement_ai.project_context import load_context
    project, artifacts, chunks = load_context(project_id)
    if project is None:
        return {"kb_status": "blocked", "kg_status": "blocked", "error": "project not found"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        kb_future = pool.submit(persist_kb, project_id, project, artifacts, chunks)
        kg_future = pool.submit(persist_kg, project_id, project, artifacts, chunks)
        kb = kb_future.result()
        kg = kg_future.result()
    return {
        "kb_status": kb.get("status") or "ready",
        "kg_status": kg.get("status") or "ready",
        "knowledge_pct": kb.get("knowledge_pct"),
        "kg_nodes": kg.get("node_count"),
        "kg_edges": kg.get("edge_count"),
        "missing": kb.get("missing") or [],
    }
