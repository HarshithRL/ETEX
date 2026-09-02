"""Procurement persistence tests."""

from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path

import pytest

from shared.db import init_db
from shared.db.connection import _SessionLocal, _engine
from shared.db.repos import artifacts as artifact_repo
from shared.db.repos import projects as project_repo
from shared.db.repos.artifacts import UploadFile
from shared.db.repos.users import upsert_user_from_identity
from services.procurement_serializers import (
    dashboard_payload,
    documents_payload,
    workspace_payload,
)

_DEFAULT_CREATE_PAYLOAD = {
    "name": "Test Project",
    "workflowEntryPoint": "Sourcing",
}


@pytest.fixture()
def db_env(monkeypatch):
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None

    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "test.sqlite"
    data_root = Path(tmp) / "data" / "projects"
    monkeypatch.setenv("MATE_SQLITE_PATH", str(db_path))
    monkeypatch.setenv("MATE_PROJECTS_DATA_ROOT", str(data_root))
    init_db()
    upsert_user_from_identity(
        {
            "user": {
                "id": "owner-1",
                "display_name": "Owner One",
                "user_name": "owner1",
                "email": "owner1@example.com",
            }
        }
    )
    upsert_user_from_identity(
        {
            "user": {
                "id": "owner-2",
                "display_name": "Owner Two",
                "user_name": "owner2",
                "email": "owner2@example.com",
            }
        }
    )
    yield {"db_path": db_path, "data_root": data_root}
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    shutil.rmtree(tmp, ignore_errors=True)


def test_project_crud_scoped_to_owner(db_env):
    created = project_repo.create(
        "owner-1",
        {
            **_DEFAULT_CREATE_PAYLOAD,
            "name": "Office Supplies",
            "category": "Office Supplies",
            "targetSpend": "1000000",
            "requirements": [{"ref": "REQ-01", "text": "Must deliver", "weight": "High"}],
        },
    )
    assert created.id
    assert created.code.startswith("PRJ-")
    assert created.workflow_entry_point == "Sourcing"

    fetched = project_repo.get_for_owner(created.id, "owner-1")
    assert fetched.name == "Office Supplies"

    with pytest.raises(project_repo.ProjectNotFoundError):
        project_repo.get_for_owner(created.id, "owner-2")

    updated = project_repo.update_for_owner(
        created.id,
        "owner-1",
        {"status": "Evaluation", "progress": 25},
    )
    assert updated.status == "Evaluation"
    assert updated.progress == 25

    rows, total = project_repo.list_for_owner("owner-1")
    assert total == 1
    assert rows[0].id == created.id

    project_repo.delete_for_owner(created.id, "owner-1")
    with pytest.raises(project_repo.ProjectNotFoundError):
        project_repo.get_for_owner(created.id, "owner-1")


def test_artifact_upload_serializes_to_documents_and_workspace(db_env):
    created = project_repo.create("owner-1", _DEFAULT_CREATE_PAYLOAD)
    upload = UploadFile(
        filename="Vendor_A.pdf",
        stream=io.BytesIO(b"%PDF-1.4 test"),
        content_type="application/pdf",
    )
    artifact_repo.create_upload(created.id, "owner-1", upload)

    artifacts = artifact_repo.list_for_project(created.id, "owner-1")
    project = project_repo.get_for_owner(created.id, "owner-1")

    docs = documents_payload(artifacts)
    assert len(docs["fileGroups"]) == 1
    assert docs["fileGroups"][0]["files"][0]["name"] == "Vendor_A.pdf"

    workspace = workspace_payload(project, artifacts, user_initial="O")
    assert workspace["files"]["inputsCount"] == 1
    assert workspace["chatMessages"] == []


def test_dashboard_counts_reflect_projects(db_env):
    upsert_user_from_identity(
        {
            "user": {
                "id": "dash-owner",
                "display_name": "Dash Owner",
                "user_name": "dash",
                "email": "dash@example.com",
            }
        }
    )
    project_repo.create(
        "dash-owner",
        {**_DEFAULT_CREATE_PAYLOAD, "name": "Active One", "targetSpend": "500000"},
    )
    project_repo.create(
        "dash-owner",
        {**_DEFAULT_CREATE_PAYLOAD, "name": "Active Two", "targetSpend": "250000"},
    )
    projects = project_repo.list_all_for_owner("dash-owner")
    payload = dashboard_payload(projects)
    assert payload["projectStatus"]["total"] == 2
    assert payload["kpis"][0]["value"] == "2"


def test_peek_next_code_does_not_insert_row(db_env):
    before, before_total = project_repo.list_for_owner("owner-1")
    preview = project_repo.peek_next_code()
    after, after_total = project_repo.list_for_owner("owner-1")
    assert preview.startswith("PRJ-")
    assert before_total == after_total
    assert len(before) == len(after)


def test_create_with_previewed_code_persists_code(db_env):
    preview = project_repo.peek_next_code()
    created = project_repo.create(
        "owner-1",
        {**_DEFAULT_CREATE_PAYLOAD, "projectId": preview, "name": "Previewed"},
    )
    assert created.code == preview


def test_create_without_code_auto_assigns(db_env):
    created = project_repo.create("owner-1", {**_DEFAULT_CREATE_PAYLOAD, "name": "Auto"})
    assert created.code.startswith("PRJ-")


def test_create_rejects_missing_workflow_entry_point(db_env):
    with pytest.raises(project_repo.ProjectValidationError, match="workflowEntryPoint"):
        project_repo.create("owner-1", {"name": "No workflow"})


def test_create_rejects_invalid_workflow_entry_point(db_env):
    with pytest.raises(project_repo.ProjectValidationError, match="workflowEntryPoint"):
        project_repo.create(
            "owner-1",
            {"name": "Bad workflow", "workflowEntryPoint": "Unknown"},
        )


def test_project_to_dict_includes_new_fields(db_env):
    created = project_repo.create(
        "owner-1",
        {
            **_DEFAULT_CREATE_PAYLOAD,
            "name": "Full Fields",
            "businessProcess": "Direct",
            "requester": "Alex",
            "dept": "Procurement",
        },
    )
    row = project_repo.project_to_dict(created)
    assert row["workflowEntryPoint"] == "Sourcing"
    assert row["businessProcess"] == "Direct"
    assert row["requester"] == "Alex"
    assert row["dept"] == "Procurement"
