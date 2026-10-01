"""Baseline: the v0.9 schema (memories, memory_relationships).

Mirrors exactly what Base.metadata.create_all() produced up to v0.9, so:
- a fresh database gets the v0.9 schema;
- an existing database created by create_all() is detected and left untouched
  (tables are only created when missing), after which later revisions apply.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("memories"):
        op.create_table(
            "memories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("importance", sa.Float(), nullable=False),
            sa.Column("embedding", Vector(384), nullable=True),
            sa.Column("access_count", sa.Integer(), nullable=False),
            sa.Column("state", sa.String(20), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("contradicted_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("last_accessed", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_contradicted", sa.Boolean(), nullable=False),
        )

    if not inspector.has_table("memory_relationships"):
        op.create_table(
            "memory_relationships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_memory_id", sa.Integer(), sa.ForeignKey("memories.id"), nullable=False),
            sa.Column("target_memory_id", sa.Integer(), sa.ForeignKey("memories.id"), nullable=False),
            sa.Column("relationship_type", sa.String(), nullable=False),
        )
        op.create_index("ix_memory_relationships_id", "memory_relationships", ["id"])


def downgrade() -> None:
    op.drop_table("memory_relationships")
    op.drop_table("memories")
