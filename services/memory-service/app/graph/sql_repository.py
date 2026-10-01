"""
PostgreSQL-backed knowledge graph repository (source of truth).

Writes happen in the caller's session/transaction, so graph updates commit or
roll back together with the memory evolution that produced them. All inserts
are idempotent (ON CONFLICT DO NOTHING against unique constraints), so
concurrent workers never create duplicate rows.

Entity resolution priority (conservative, deterministic):
    1. exact normalized entity name
    2. explicit alias (entity_aliases)
    (no fuzzy or embedding-based identity: similar names stay distinct)
"""

import re

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.graph.db_models import Entity, EntityAlias, EntityRelationship, MemoryEntity
from app.graph.graph_models import GraphEdge, GraphNode, KnowledgeGraph
from app.understanding.entity_normalizer import normalize_entity_name

USER_ENTITY = "user"
MAX_QUERY_SPAN = 5  # longest entity name (in words) matched in a query


class SqlGraphRepository:

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------- writes

    def upsert_entity(self, name: str, entity_type: str = "CONCEPT") -> int | None:
        key = normalize_entity_name(name)
        if not key:
            return None
        existing = self._resolve_key(key)
        if existing is not None:
            return existing
        self.db.execute(
            pg_insert(Entity.__table__)
            .values(normalized_name=key, display_name=name.strip()[:255], entity_type=entity_type)
            .on_conflict_do_nothing(index_elements=["normalized_name"])
        )
        return self.db.execute(
            select(Entity.id).where(Entity.normalized_name == key)
        ).scalar_one()

    def add_alias(self, entity_id: int, alias: str) -> None:
        """Explicitly record that `alias` names `entity_id` (requires explicit evidence)."""
        key = normalize_entity_name(alias)
        if not key:
            return
        self.db.execute(
            pg_insert(EntityAlias.__table__)
            .values(entity_id=entity_id, alias_normalized=key)
            .on_conflict_do_nothing(index_elements=["alias_normalized"])
        )

    def link_memory(self, memory_id: int, entity_id: int, role: str = "mention") -> None:
        self.db.execute(
            pg_insert(MemoryEntity.__table__)
            .values(memory_id=memory_id, entity_id=entity_id, role=role)
            .on_conflict_do_nothing(index_elements=["memory_id", "entity_id"])
        )

    def add_relationship(self, source_id: int, target_id: int, relationship_type: str, memory_id: int) -> None:
        if source_id == target_id:
            return
        self.db.execute(
            pg_insert(EntityRelationship.__table__)
            .values(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=relationship_type,
                memory_id=memory_id,
            )
            .on_conflict_do_nothing(constraint="uq_entity_relationships_edge_memory")
        )

    def unlink_memory(self, memory_id: int) -> None:
        """Remove a memory's entity links and the relationships it supports."""
        self.db.execute(delete(EntityRelationship).where(EntityRelationship.memory_id == memory_id))
        self.db.execute(delete(MemoryEntity).where(MemoryEntity.memory_id == memory_id))

    def delete_orphan_entities(self) -> int:
        """
        Delete entities no memory mentions and no relationship or explicit
        alias references. Aliased entities are kept (aliases are explicit data).
        """
        result = self.db.execute(
            delete(Entity).where(
                ~exists().where(MemoryEntity.entity_id == Entity.id),
                ~exists().where(EntityAlias.entity_id == Entity.id),
                ~exists().where(
                    (EntityRelationship.source_entity_id == Entity.id)
                    | (EntityRelationship.target_entity_id == Entity.id)
                ),
            )
        )
        return result.rowcount

    # -------------------------------------------------------------- reads

    def _resolve_key(self, key: str) -> int | None:
        entity_id = self.db.execute(
            select(Entity.id).where(Entity.normalized_name == key)
        ).scalar_one_or_none()
        if entity_id is not None:
            return entity_id
        return self.db.execute(
            select(EntityAlias.entity_id).where(EntityAlias.alias_normalized == key)
        ).scalar_one_or_none()

    def resolve(self, name: str) -> int | None:
        """Entity id for a name: exact normalized name, else explicit alias, else None."""
        key = normalize_entity_name(name)
        return self._resolve_key(key) if key else None

    def resolve_query_entities(self, text: str) -> list[int]:
        """
        Entities named in free text, by longest-span exact matching.

        "Where does Rahul Sharma work?" resolves 'rahul sharma' and does NOT
        also resolve the shorter 'rahul' inside it.
        """
        words = re.findall(r"[\w'-]+", text.lower())
        spans = {}
        for n in range(min(MAX_QUERY_SPAN, len(words)), 0, -1):
            for i in range(len(words) - n + 1):
                spans.setdefault(" ".join(words[i:i + n]), (i, i + n))
        if not spans:
            return []

        keys = list(spans)
        names = dict(self.db.execute(
            select(Entity.normalized_name, Entity.id).where(Entity.normalized_name.in_(keys))
        ).all())
        aliases = dict(self.db.execute(
            select(EntityAlias.alias_normalized, EntityAlias.entity_id).where(EntityAlias.alias_normalized.in_(keys))
        ).all())

        covered = set()
        resolved = []
        for key in sorted(keys, key=lambda k: -(spans[k][1] - spans[k][0])):
            entity_id = names.get(key, aliases.get(key))
            if entity_id is None or key == USER_ENTITY:
                continue
            start, end = spans[key]
            if any(pos in covered for pos in range(start, end)):
                continue
            covered.update(range(start, end))
            if entity_id not in resolved:
                resolved.append(entity_id)
        return resolved

    def memory_ids_for_entities(self, entity_ids: list[int]) -> set[int]:
        if not entity_ids:
            return set()
        rows = self.db.execute(
            select(MemoryEntity.memory_id).where(MemoryEntity.entity_id.in_(entity_ids))
        ).all()
        return {row[0] for row in rows}

    def memory_ids_for_query(self, text: str) -> set[int]:
        return self.memory_ids_for_entities(self.resolve_query_entities(text))

    def load(self) -> KnowledgeGraph:
        """Materialize the persisted graph in the legacy KnowledgeGraph shape."""
        entities = self.db.execute(
            select(Entity.id, Entity.normalized_name, Entity.display_name, Entity.entity_type)
        ).all()
        names = {row.id: row.normalized_name for row in entities}
        memory_links = {}
        for memory_id, entity_id in self.db.execute(
            select(MemoryEntity.memory_id, MemoryEntity.entity_id)
        ).all():
            memory_links.setdefault(entity_id, []).append(memory_id)

        nodes = [
            GraphNode(
                id=row.normalized_name,
                label=row.display_name,
                type=row.entity_type,
                memory_ids=sorted(memory_links.get(row.id, [])),
            )
            for row in entities
        ]
        edge_keys = {
            (names[s], names[t], r)
            for s, t, r in self.db.execute(
                select(
                    EntityRelationship.source_entity_id,
                    EntityRelationship.target_entity_id,
                    EntityRelationship.relationship_type,
                ).distinct()
            ).all()
        }
        edges = [GraphEdge(source=s, target=t, relationship=r) for s, t, r in sorted(edge_keys)]
        return KnowledgeGraph(nodes=nodes, edges=edges)
