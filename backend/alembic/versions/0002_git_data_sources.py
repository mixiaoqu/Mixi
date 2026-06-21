"""add git data sources

Revision ID: 0002_git_data_sources
Revises: 0001_initial_schema
Create Date: 2026-06-20 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_git_data_sources"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "git_data_sources",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("repository_url", sa.String(length=1024), nullable=False),
        sa.Column("auth_type", sa.String(length=20), server_default="public", nullable=False),
        sa.Column("encrypted_credential", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="connected", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "repository_url", name="uq_git_data_source_user_url"),
    )
    op.create_index(op.f("ix_git_data_sources_user_id"), "git_data_sources", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_git_data_sources_user_id"), table_name="git_data_sources")
    op.drop_table("git_data_sources")
