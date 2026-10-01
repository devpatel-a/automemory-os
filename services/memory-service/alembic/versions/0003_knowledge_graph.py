"""Persistent knowledge graph: entities, aliases, memory links, relationships.

Additive only. The previous graph lived in process memory and is not
recoverable here; it is rebuilt as memories are processed.

Revision ID: 0003_knowledge_graph
Revises: 0002_integrity_constraints
Create Date: 2026-09-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_knowledge_graph"
down_revision = "0002_integrity_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), server_default="CONCEPT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("normalized_name", name="entities_normalized_name_key"),
    )
    op.create_table(
        "entity_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_normalized", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("alias_normalized", name="entity_aliases_alias_normalized_key"),
    )
    op.create_index("ix_entity_aliases_entity_id", "entity_aliases", ["entity_id"])
    op.create_table(
        "memory_entities",
        sa.Column("memory_id", sa.Integer(), sa.ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(20), server_default="mention", nullable=False),
    )
    op.create_index("ix_memory_entities_entity_id", "memory_entities", ["entity_id"])
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(64), nullable=False),
        sa.Column("memory_id", sa.Integer(), sa.ForeignKey("memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "source_entity_id", "target_entity_id", "relationship_type", "memory_id",
            name="uq_entity_relationships_edge_memory",
        ),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_entity_relationships_no_self_link"),
    )
    op.create_index("ix_entity_relationships_source_type", "entity_relationships", ["source_entity_id", "relationship_type"])
    op.create_index("ix_entity_relationships_target_entity_id", "entity_relationships", ["target_entity_id"])
    op.create_index("ix_entity_relationships_memory_id", "entity_relationships", ["memory_id"])


def downgrade() -> None:
    op.drop_table("entity_relationships")
    op.drop_table("memory_entities")
    op.drop_table("entity_aliases")
    op.drop_table("entities")
