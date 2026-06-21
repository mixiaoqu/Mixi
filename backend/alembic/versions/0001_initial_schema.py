"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-19 13:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


membership_role = postgresql.ENUM(
    "owner", "admin", "editor", "viewer", name="membership_role", create_type=False
)
workspace_status = postgresql.ENUM("active", "archived", name="workspace_status", create_type=False)
agent_status = postgresql.ENUM(
    "draft", "active", "paused", "archived", name="agent_status", create_type=False
)
knowledge_base_status = postgresql.ENUM(
    "active", "syncing", "archived", name="knowledge_base_status", create_type=False
)
document_index_status = postgresql.ENUM(
    "pending", "indexing", "ready", "failed", name="document_index_status", create_type=False
)
workflow_run_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "cancelled", name="workflow_run_status", create_type=False
)
workflow_step_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "cancelled", name="workflow_step_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    membership_role.create(bind, checkfirst=True)
    workspace_status.create(bind, checkfirst=True)
    agent_status.create(bind, checkfirst=True)
    knowledge_base_status.create(bind, checkfirst=True)
    document_index_status.create(bind, checkfirst=True)
    workflow_run_status.create(bind, checkfirst=True)
    workflow_step_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("auth_provider", sa.String(length=40), server_default="password", nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "workspaces",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", workspace_status, server_default="active", nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_workspaces_owner_user_id"), "workspaces", ["owner_user_id"], unique=False)

    op.create_table(
        "workspace_memberships",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", membership_role, server_default="viewer", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership"),
    )
    op.create_index(op.f("ix_workspace_memberships_user_id"), "workspace_memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_workspace_memberships_workspace_id"), "workspace_memberships", ["workspace_id"], unique=False)

    op.create_table(
        "agents",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.String(length=80), server_default="gpt-4.1-mini", nullable=False),
        sa.Column("status", agent_status, server_default="draft", nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_agent_workspace_slug"),
    )
    op.create_index(op.f("ix_agents_workspace_id"), "agents", ["workspace_id"], unique=False)

    op.create_table(
        "knowledge_bases",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vector_collection", sa.String(length=160), nullable=True),
        sa.Column("embedding_model", sa.String(length=120), nullable=True),
        sa.Column("status", knowledge_base_status, server_default="active", nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_knowledge_base_workspace_name"),
    )
    op.create_index(op.f("ix_knowledge_bases_workspace_id"), "knowledge_bases", ["workspace_id"], unique=False)

    op.create_table(
        "knowledge_documents",
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=40), server_default="upload", nullable=False),
        sa.Column("source_uri", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("index_status", document_index_status, server_default="pending", nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_base_id", "checksum", name="uq_knowledge_document_checksum"),
    )
    op.create_index(op.f("ix_knowledge_documents_knowledge_base_id"), "knowledge_documents", ["knowledge_base_id"], unique=False)

    op.create_table(
        "workflow_runs",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("initiated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("trigger_source", sa.String(length=40), server_default="manual", nullable=False),
        sa.Column("status", workflow_run_status, server_default="queued", nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_runs_agent_id"), "workflow_runs", ["agent_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_initiated_by_user_id"), "workflow_runs", ["initiated_by_user_id"], unique=False)
    op.create_index(op.f("ix_workflow_runs_workspace_id"), "workflow_runs", ["workspace_id"], unique=False)

    op.create_table(
        "workflow_run_steps",
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(length=120), nullable=False),
        sa.Column("step_name", sa.String(length=120), nullable=False),
        sa.Column("status", workflow_step_status, nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_run_id", "sequence_no", name="uq_workflow_run_step_sequence"),
    )
    op.create_index("ix_workflow_run_steps_run_status", "workflow_run_steps", ["workflow_run_id", "status"], unique=False)
    op.create_index(op.f("ix_workflow_run_steps_workflow_run_id"), "workflow_run_steps", ["workflow_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_run_steps_workflow_run_id"), table_name="workflow_run_steps")
    op.drop_index("ix_workflow_run_steps_run_status", table_name="workflow_run_steps")
    op.drop_table("workflow_run_steps")

    op.drop_index(op.f("ix_workflow_runs_workspace_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_initiated_by_user_id"), table_name="workflow_runs")
    op.drop_index(op.f("ix_workflow_runs_agent_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index(op.f("ix_knowledge_documents_knowledge_base_id"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_index(op.f("ix_knowledge_bases_workspace_id"), table_name="knowledge_bases")
    op.drop_table("knowledge_bases")

    op.drop_index(op.f("ix_agents_workspace_id"), table_name="agents")
    op.drop_table("agents")

    op.drop_index(op.f("ix_workspace_memberships_workspace_id"), table_name="workspace_memberships")
    op.drop_index(op.f("ix_workspace_memberships_user_id"), table_name="workspace_memberships")
    op.drop_table("workspace_memberships")

    op.drop_index(op.f("ix_workspaces_owner_user_id"), table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_table("user_sessions")

    op.drop_table("users")

    bind = op.get_bind()
    workflow_step_status.drop(bind, checkfirst=True)
    workflow_run_status.drop(bind, checkfirst=True)
    document_index_status.drop(bind, checkfirst=True)
    knowledge_base_status.drop(bind, checkfirst=True)
    agent_status.drop(bind, checkfirst=True)
    workspace_status.drop(bind, checkfirst=True)
    membership_role.drop(bind, checkfirst=True)
