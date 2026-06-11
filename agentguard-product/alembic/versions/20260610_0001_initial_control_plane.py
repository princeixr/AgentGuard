"""initial control plane persistence

Revision ID: 20260610_0001
Revises:
Create Date: 2026-06-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260610_0001"
down_revision = None
branch_labels = None
depends_on = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=True),
        sa.Column("scopes", _json_type(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_id"),
    )
    op.create_table(
        "runtime_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("record_type", sa.String(length=64), nullable=False),
        sa.Column("record_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=True),
        sa.Column("agent_id", sa.String(length=128), nullable=True),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_records_type_id",
        "runtime_records",
        ["record_type", "record_id"],
        unique=True,
    )
    op.create_index(
        "ix_runtime_records_agent_session",
        "runtime_records",
        ["agent_id", "session_id"],
    )
    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.String(length=128), nullable=False),
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("call_id", sa.String(length=255), nullable=False),
        sa.Column("workspace_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("deployment_id", sa.String(length=128), nullable=False),
        sa.Column("integration_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("turn_id", sa.String(length=128), nullable=False),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("approval_id"),
    )
    op.create_index(
        "ix_approvals_status_created_at",
        "approvals",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_approvals_agent_session",
        "approvals",
        ["agent_id", "session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_approvals_agent_session", table_name="approvals")
    op.drop_index("ix_approvals_status_created_at", table_name="approvals")
    op.drop_table("approvals")
    op.drop_index("ix_runtime_records_agent_session", table_name="runtime_records")
    op.drop_index("ix_runtime_records_type_id", table_name="runtime_records")
    op.drop_table("runtime_records")
    op.drop_table("api_keys")
