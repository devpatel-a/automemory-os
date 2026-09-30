"""Integrity constraints and indexes for memories and memory_relationships.

Existing data is never deleted, with one lossless exception: rows in
memory_relationships that are exact duplicates of another row (same source,
target and type) are collapsed, which the new unique constraint requires.

CHECK and self-referencing FK constraints are created NOT VALID (enforced for
all new writes) and then validated only if existing rows already satisfy
them, so legacy anomalies block nothing and are reported instead of erased.

Revision ID: 0002_integrity_constraints
Revises: 0001_baseline
Create Date: 2026-09-30
"""

import logging

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")

revision = "0002_integrity_constraints"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _drop_foreign_keys(table: str, column: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for fk in inspector.get_foreign_keys(table):
        if fk["constrained_columns"] == [column] and fk.get("name"):
            op.drop_constraint(fk["name"], table, type_="foreignkey")


def _add_check_not_valid(table: str, name: str, condition: str) -> None:
    op.execute(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition}) NOT VALID")
    violations = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM {table} WHERE NOT ({condition})")
    ).scalar()
    if violations == 0:
        op.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}")
    else:
        logger.warning(
            "%s: %d legacy row(s) violate the constraint; left NOT VALID "
            "(enforced for new writes only).", name, violations,
        )


def upgrade() -> None:
    bind = op.get_bind()

    # ---- memory_relationships -------------------------------------------
    bind.execute(sa.text(
        "DELETE FROM memory_relationships a USING memory_relationships b "
        "WHERE a.id > b.id AND a.source_memory_id = b.source_memory_id "
        "AND a.target_memory_id = b.target_memory_id "
        "AND a.relationship_type = b.relationship_type"
    ))

    _drop_foreign_keys("memory_relationships", "source_memory_id")
    _drop_foreign_keys("memory_relationships", "target_memory_id")
    op.create_foreign_key(
        "fk_memory_relationships_source", "memory_relationships", "memories",
        ["source_memory_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_memory_relationships_target", "memory_relationships", "memories",
        ["target_memory_id"], ["id"], ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_memory_relationships_source_target_type", "memory_relationships",
        ["source_memory_id", "target_memory_id", "relationship_type"],
    )
    _add_check_not_valid(
        "memory_relationships", "ck_memory_relationships_no_self_link",
        "source_memory_id <> target_memory_id",
    )
    op.create_index(
        "ix_memory_relationships_source_type", "memory_relationships",
        ["source_memory_id", "relationship_type"],
    )
    op.create_index(
        "ix_memory_relationships_target_memory_id", "memory_relationships",
        ["target_memory_id"],
    )

    # ---- memories ---------------------------------------------------------
    op.execute(
        "ALTER TABLE memories ADD CONSTRAINT fk_memories_contradicted_by "
        "FOREIGN KEY (contradicted_by_id) REFERENCES memories (id) "
        "ON DELETE SET NULL NOT VALID"
    )
    dangling = bind.execute(sa.text(
        "SELECT count(*) FROM memories m WHERE m.contradicted_by_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM memories t WHERE t.id = m.contradicted_by_id)"
    )).scalar()
    if dangling == 0:
        op.execute("ALTER TABLE memories VALIDATE CONSTRAINT fk_memories_contradicted_by")
    else:
        logger.warning(
            "fk_memories_contradicted_by: %d dangling reference(s); left NOT VALID "
            "(enforced for new writes only).", dangling,
        )

    _add_check_not_valid(
        "memories", "ck_memories_state", "state IN ('active', 'weak', 'archived')",
    )
    _add_check_not_valid(
        "memories", "ck_memories_not_self_contradicted",
        "contradicted_by_id IS NULL OR contradicted_by_id <> id",
    )
    op.create_index("ix_memories_state", "memories", ["state"])
    op.create_index("ix_memories_contradicted_by_id", "memories", ["contradicted_by_id"])
    op.execute(
        "CREATE INDEX ix_memories_content_fts ON memories "
        "USING gin (to_tsvector('english', content))"
    )
    op.execute(
        "CREATE INDEX ix_memories_embedding_hnsw ON memories "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_memories_embedding_hnsw", table_name="memories")
    op.drop_index("ix_memories_content_fts", table_name="memories")
    op.drop_index("ix_memories_contradicted_by_id", table_name="memories")
    op.drop_index("ix_memories_state", table_name="memories")
    op.drop_constraint("ck_memories_not_self_contradicted", "memories", type_="check")
    op.drop_constraint("ck_memories_state", "memories", type_="check")
    op.drop_constraint("fk_memories_contradicted_by", "memories", type_="foreignkey")

    op.drop_index("ix_memory_relationships_target_memory_id", table_name="memory_relationships")
    op.drop_index("ix_memory_relationships_source_type", table_name="memory_relationships")
    op.drop_constraint("ck_memory_relationships_no_self_link", "memory_relationships", type_="check")
    op.drop_constraint("uq_memory_relationships_source_target_type", "memory_relationships", type_="unique")
    op.drop_constraint("fk_memory_relationships_target", "memory_relationships", type_="foreignkey")
    op.drop_constraint("fk_memory_relationships_source", "memory_relationships", type_="foreignkey")
    op.create_foreign_key(None, "memory_relationships", "memories", ["source_memory_id"], ["id"])
    op.create_foreign_key(None, "memory_relationships", "memories", ["target_memory_id"], ["id"])
