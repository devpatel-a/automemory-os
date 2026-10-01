"""Provenance: memory_evidence.

Existing memories get exactly one evidence row with source_type='legacy' and
observed_at = created_at. Nothing else is invented: no raw text, extraction
method, message or conversation is fabricated for legacy records.

Revision ID: 0004_memory_evidence
Revises: 0003_knowledge_graph
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_memory_evidence"
down_revision = "0003_knowledge_graph"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("memory_id", sa.Integer(), sa.ForeignKey("memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("conversation_id", sa.String(255), nullable=True),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("extraction_method", sa.String(64), nullable=True),
        sa.Column("extractor_version", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("reason_codes", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_memory_evidence_memory_id", "memory_evidence", ["memory_id"])
    op.execute(
        "INSERT INTO memory_evidence (memory_id, source_type, observed_at) "
        "SELECT id, 'legacy', created_at FROM memories"
    )


def downgrade() -> None:
    op.drop_table("memory_evidence")
