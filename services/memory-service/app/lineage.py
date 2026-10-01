"""
Memory lineage vocabulary and lookups (memory_relationships).

    old fact  --superseded_by-->  new fact      (temporal transition; old stays 'active')
    duplicate --merged_into----->  canonical     (duplicate archived; evidence preserved)
    plan      --fulfilled_by---->  current fact  (a FUTURE plan that actually happened)

Contradiction lineage lives on the memory row itself
(is_contradicted / contradicted_by_id) for backward compatibility.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models_relationship import MemoryRelationship

SUPERSEDED_BY = "superseded_by"
MERGED_INTO = "merged_into"
FULFILLED_BY = "fulfilled_by"

# A memory with one of these outgoing links is effectively HISTORICAL:
# it no longer describes the current state (but stays queryable for history).
HISTORICAL_LINEAGE_TYPES = (SUPERSEDED_BY, FULFILLED_BY)


def historical_memory_ids(db, memory_ids) -> set[int]:
    """IDs among memory_ids that have a historical lineage link (single query)."""
    ids = [mid for mid in memory_ids if mid is not None]
    if not ids:
        return set()
    rows = (
        db.query(MemoryRelationship.source_memory_id)
        .filter(
            MemoryRelationship.relationship_type.in_(HISTORICAL_LINEAGE_TYPES),
            MemoryRelationship.source_memory_id.in_(ids),
        )
        .all()
    )
    return {row[0] for row in rows}


def link(db, source_memory_id: int, target_memory_id: int, relationship_type: str) -> None:
    """
    Idempotently record a lineage relationship.

    Uses INSERT ... ON CONFLICT DO NOTHING against the unique
    (source, target, type) constraint, so concurrent writers cannot create
    duplicate rows. Self-links are rejected (also enforced by a CHECK constraint).
    """
    if source_memory_id == target_memory_id:
        raise ValueError(f"refusing self-referential {relationship_type} link on memory {source_memory_id}")
    db.execute(
        pg_insert(MemoryRelationship.__table__)
        .values(
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relationship_type=relationship_type,
        )
        .on_conflict_do_nothing(
            index_elements=["source_memory_id", "target_memory_id", "relationship_type"]
        )
    )
