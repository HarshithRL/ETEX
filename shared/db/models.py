"""SQLAlchemy ORM models for Mate hub, users, projects, and artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Base(DeclarativeBase):
    pass


class HubModule(Base):
    __tablename__ = "hub_module"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String)
    path: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    user_grants: Mapped[list[UserModule]] = relationship(back_populates="module")
    projects: Mapped[list[Project]] = relationship(back_populates="module")


class AppUser(Base):
    __tablename__ = "app_user"

    workspace_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_name: Mapped[str | None] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)

    module_grants: Mapped[list[UserModule]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[Project]] = relationship(back_populates="owner")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="uploader")


class UserModule(Base):
    __tablename__ = "user_module"
    __table_args__ = (
        UniqueConstraint("workspace_id", "module_id", name="uq_user_module"),
    )

    workspace_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("app_user.workspace_id", ondelete="CASCADE"),
        primary_key=True,
    )
    module_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("hub_module.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    granted_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)

    user: Mapped[AppUser] = relationship(back_populates="module_grants")
    module: Mapped[HubModule] = relationship(back_populates="user_grants")


class Project(Base):
    __tablename__ = "project"
    __table_args__ = (
        Index("ix_project_owner_id", "owner_id"),
        Index("ix_project_module_owner", "module_id", "owner_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("app_user.workspace_id", ondelete="RESTRICT"),
        nullable=False,
    )
    module_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("hub_module.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    workflow_entry_point: Mapped[str | None] = mapped_column(String)
    business_process: Mapped[str | None] = mapped_column(String)
    requester: Mapped[str | None] = mapped_column(String)
    dept: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Active")
    priority: Mapped[str] = mapped_column(String, nullable=False, default="Medium")
    budget: Mapped[str | None] = mapped_column(String)
    award_horizon: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deadline: Mapped[str | None] = mapped_column(String)
    requirements_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)
    updated_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)

    owner: Mapped[AppUser] = relationship(back_populates="projects")
    module: Mapped[HubModule] = relationship(back_populates="projects")
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class Artifact(Base):
    __tablename__ = "artifact"
    __table_args__ = (
        Index("ix_artifact_project_folder", "project_id", "folder"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by: Mapped[str] = mapped_column(
        String,
        ForeignKey("app_user.workspace_id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    folder: Mapped[str | None] = mapped_column(String)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    storage_relpath: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=utc_now_iso)

    project: Mapped[Project] = relationship(back_populates="artifacts")
    uploader: Mapped[AppUser] = relationship(back_populates="artifacts")


def identity_user_payload(user: dict[str, Any] | None) -> dict[str, str | None]:
    if not isinstance(user, dict):
        return {
            "workspace_id": "",
            "user_name": None,
            "display_name": None,
            "email": None,
        }
    return {
        "workspace_id": str(user.get("id") or "").strip(),
        "user_name": _optional_str(user.get("user_name")),
        "display_name": _optional_str(user.get("display_name")),
        "email": _optional_str(user.get("email")),
    }


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
