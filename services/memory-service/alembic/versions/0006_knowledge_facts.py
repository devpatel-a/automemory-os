"""knowledge_facts: derived structural fact index (schema only).

Schema only, by design: rows are derived by the spaCy-based fact extractor,
which must not run inside a migration (slow, model-dependent, hard to roll
back). Populate or refresh rows with the explicit utility:

    python -m app.knowledge.fact_index reindex
    python -m app.knowledge.fact_index check

Until reindexed, existing memories simply have no row. The index is a shadow
index (not read by evolution yet), so this changes no behaviour. Downgrade
drops only derived data.

Revision ID: 0006_knowledge_facts
Revises: 0005_memory_version
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_knowledge_facts"
down_revision = "0005_memory_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_facts",
        sa.Column(
            "memory_id", sa.Integer(),
            sa.ForeignKey("memories.id", ondelete="CASCADE", name="fk_knowledge_facts_memory"),
            primary_key=True,
        ),
        sa.Column("entity_key", sa.String(255), nullable=False),
        sa.Column("attribute_key", sa.String(128), nullable=False),
        sa.Column("value_key", sa.String(255), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False),
        sa.Column("fact_type", sa.String(32), nullable=False),
        sa.Column("single_valued", sa.Boolean(), nullable=False),
        sa.Column("temporal_state", sa.String(16), nullable=False),
        sa.Column("is_negated", sa.Boolean(), nullable=False),
        sa.Column("is_placeholder", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("extractor_version", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "temporal_state IN ('CURRENT', 'HISTORICAL', 'FUTURE', 'UNKNOWN')",
            name="ck_knowledge_facts_temporal_state",
        ),
        sa.CheckConstraint("entity_key <> '' AND attribute_key <> ''", name="ck_knowledge_facts_keys_not_empty"),
        sa.CheckConstraint("char_length(content_sha256) = 64", name="ck_knowledge_facts_content_sha256"),
    )
    op.create_index(
        "ix_knowledge_facts_domain_value", "knowledge_facts",
        ["entity_key", "attribute_key", "value_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_facts_domain_value", table_name="knowledge_facts")
    op.drop_table("knowledge_facts")
