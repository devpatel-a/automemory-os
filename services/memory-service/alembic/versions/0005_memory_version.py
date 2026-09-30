"""Optimistic concurrency version on memories; previous text on evidence.

- memories.version: incremented by every semantic mutation (content,
  lifecycle state, contradiction, lineage, archive, admin edit). Evolution
  re-verifies it after locking a target, so a decision reasoned on stale
  state is never applied. Existing rows start at 1.
- memory_evidence.previous_text: the text a memory held before an
  administrative edit (PUT), so edits never make the original unrecoverable.

Additive only; no existing data changes.

Revision ID: 0005_memory_version
Revises: 0004_memory_evidence
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_memory_version"
down_revision = "0004_memory_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "memories",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("memory_evidence", sa.Column("previous_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("memory_evidence", "previous_text")
    op.drop_column("memories", "version")
