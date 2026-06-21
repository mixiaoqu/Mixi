from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class MembershipRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


class WorkspaceStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class AgentStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class KnowledgeBaseStatus(str, enum.Enum):
    active = "active"
    syncing = "syncing"
    archived = "archived"


class DocumentIndexStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(String(40), default="password", server_default="password", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owned_workspaces: Mapped[list[Workspace]] = relationship(back_populates="owner")
    memberships: Mapped[list[WorkspaceMembership]] = relationship(back_populates="user", passive_deletes=True)
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", passive_deletes=True)
    git_data_sources: Mapped[list[GitDataSource]] = relationship(back_populates="user", passive_deletes=True)


class UserSession(BaseModel):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class GitDataSource(BaseModel):
    __tablename__ = "git_data_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "repository_url", name="uq_git_data_source_user_url"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    repository_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(20), default="public", server_default="public", nullable=False)
    encrypted_credential: Mapped[str | None] = mapped_column(Text)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="connected", server_default="connected", nullable=False)

    user: Mapped[User] = relationship(back_populates="git_data_sources")


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WorkspaceStatus] = mapped_column(
        Enum(WorkspaceStatus, name="workspace_status"),
        default=WorkspaceStatus.active,
        server_default=WorkspaceStatus.active.value,
        nullable=False,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    owner: Mapped[User] = relationship(back_populates="owned_workspaces")
    memberships: Mapped[list[WorkspaceMembership]] = relationship(back_populates="workspace", passive_deletes=True)
    agents: Mapped[list[Agent]] = relationship(back_populates="workspace", passive_deletes=True)
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(back_populates="workspace", passive_deletes=True)
    workflow_runs: Mapped[list[WorkflowRun]] = relationship(back_populates="workspace", passive_deletes=True)


class WorkspaceMembership(BaseModel):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole, name="membership_role"),
        default=MembershipRole.viewer,
        server_default=MembershipRole.viewer.value,
        nullable=False,
    )

    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Agent(BaseModel):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_agent_workspace_slug"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str] = mapped_column(String(80), default="gpt-4.1-mini", server_default="gpt-4.1-mini", nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"),
        default=AgentStatus.draft,
        server_default=AgentStatus.draft.value,
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="agents")
    workflow_runs: Mapped[list[WorkflowRun]] = relationship(back_populates="agent", passive_deletes=True)


class KnowledgeBase(BaseModel):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_knowledge_base_workspace_name"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    vector_collection: Mapped[str | None] = mapped_column(String(160))
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        Enum(KnowledgeBaseStatus, name="knowledge_base_status"),
        default=KnowledgeBaseStatus.active,
        server_default=KnowledgeBaseStatus.active.value,
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)

    workspace: Mapped[Workspace] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list[KnowledgeDocument]] = relationship(back_populates="knowledge_base", passive_deletes=True)


class KnowledgeDocument(BaseModel):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "checksum", name="uq_knowledge_document_checksum"),
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="upload", server_default="upload", nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    index_status: Mapped[DocumentIndexStatus] = mapped_column(
        Enum(DocumentIndexStatus, name="document_index_status"),
        default=DocumentIndexStatus.pending,
        server_default=DocumentIndexStatus.pending.value,
        nullable=False,
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")


class WorkflowRun(BaseModel):
    __tablename__ = "workflow_runs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"), index=True)
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    trigger_source: Mapped[str] = mapped_column(String(40), default="manual", server_default="manual", nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="workflow_run_status"),
        default=RunStatus.queued,
        server_default=RunStatus.queued.value,
        nullable=False,
    )
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workspace: Mapped[Workspace] = relationship(back_populates="workflow_runs")
    agent: Mapped[Agent | None] = relationship(back_populates="workflow_runs")
    steps: Mapped[list[WorkflowRunStep]] = relationship(back_populates="workflow_run", passive_deletes=True)


class WorkflowRunStep(BaseModel):
    __tablename__ = "workflow_run_steps"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "sequence_no", name="uq_workflow_run_step_sequence"),
        Index("ix_workflow_run_steps_run_status", "workflow_run_id", "status"),
    )

    workflow_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    step_key: Mapped[str] = mapped_column(String(120), nullable=False)
    step_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="workflow_step_status"), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow_run: Mapped[WorkflowRun] = relationship(back_populates="steps")
