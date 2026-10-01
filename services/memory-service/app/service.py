from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import desc, exists, func, select
from sqlalchemy.orm import Session

from . import lineage
from .database import SessionLocal
from .lineage import HISTORICAL_LINEAGE_TYPES
from .models import Memory
from .models_relationship import MemoryRelationship

from .semantic.semantic_service import (
    generate_embedding,
    semantic_search,
)

from .duplicate_service import (
    find_duplicate,
    strengthen_memory,
)


def _persist(db: Session, obj, commit: bool):
    """Commit + refresh (standalone use) or flush only (inside a caller-owned transaction)."""
    if commit:
        db.commit()
        db.refresh(obj)
    else:
        db.flush()
    return obj


def bump_version(memory: Memory) -> None:
    """Record a semantic mutation (content, lifecycle, contradiction, lineage)."""
    memory.version = (memory.version or 1) + 1


def fact_domain_key(fact) -> str | None:
    """Serialization key for statements about the same (entity, attribute)."""
    if fact is None or not fact.attribute:
        return None
    return f"fact-domain:{fact.entity.strip().lower()}|{fact.attribute.strip().lower()}"


def lock_fact_domains(db: Session, facts) -> None:
    """
    Transaction-scoped advisory locks per fact domain, taken in a stable order.

    Classification of a statement and the write it leads to happen under this
    lock, so two concurrent statements about the same (entity, attribute) can
    never both be classified against a state that the other is changing
    (e.g. two conflicting residences both stored as NEW).
    """
    keys = sorted({k for k in (fact_domain_key(f) for f in facts) if k})
    for key in keys:
        db.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))


def lock_memory(db: Session, memory: Memory) -> Memory:
    """Re-read a memory with a row lock (SELECT ... FOR UPDATE) for the current transaction."""
    return (
        db.query(Memory)
        .filter(Memory.id == memory.id)
        .with_for_update()
        .populate_existing()
        .one()
    )


def get_memory_object(item):
    if hasattr(item, "content"):
        return item
    if hasattr(item, "__getitem__"):
        return item[0]
    return item


def calculate_importance(category: str) -> float:
    scores = {
        "profile": 0.95,
        "preference": 0.80,
        "habit": 0.70,
        "event": 0.50,
    }

    return scores.get(category.lower(), 0.40)


def update_memory_state(memory: Memory):
    # Access-driven lifecycle only moves between active/weak. Leaving 'archived'
    # is an explicit evolution decision (merge/contradiction lineage), never a
    # side effect of access counting.
    if memory.state == "archived":
        return
    if memory.access_count >= 3:
        memory.state = "active"
    else:
        memory.state = "weak"


def decay_memory(memory: Memory):
    """
    Demote low-importance, rarely accessed memories to 'weak'.

    Decay never archives: 'archived' is reserved for merged duplicates and
    contradicted memories. Rarely accessed != false, and archiving here used to
    hide freshly reinforced memories (e.g. a repeated low-importance fact).
    """
    if (
        memory.state == "active"
        and memory.importance < 0.5
        and memory.access_count < 3
    ):
        memory.state = "weak"


def create_memory(
    content: str,
    category: str,
    db: Session | None = None,
    embedding: list[float] | None = None,
    semantic_dedupe: bool = True,
    commit: bool = True,
):
    """
    Store or reinforce a memory with optional database session reuse.

    - embedding: precomputed embedding for content (avoids re-embedding).
    - semantic_dedupe=False: never fold the statement into a *different*
      semantically similar memory (required when the statement is a competing
      claim, e.g. the new side of a contradiction).
    - commit=False: flush only; the caller owns the transaction.
    """
    db_session = db if db is not None else SessionLocal()

    try:
        # Serialize concurrent writers of the same statement (released at
        # transaction end), so two simultaneous inserts of identical content
        # cannot both miss the exact-match check.
        db_session.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(content)))
        )

        # Prefer a live (non-archived) exact match. Memories with historical
        # lineage (superseded / fulfilled) describe the past: a new statement
        # with the same text is a new current assertion, not a reinforcement.
        historical_link = exists().where(
            MemoryRelationship.source_memory_id == Memory.id,
            MemoryRelationship.relationship_type.in_(HISTORICAL_LINEAGE_TYPES),
        )
        existing = (
            db_session.query(Memory)
            .filter(
                Memory.content == content,
                ~historical_link,
            )
            .order_by((Memory.state == "archived").asc(), Memory.id.asc())
            # Row lock: other paths (pipeline reinforcement) update this row
            # under FOR UPDATE; a plain read here would lose their updates.
            .with_for_update(of=Memory)
            .populate_existing()
            .first()
        )

        if existing is not None and existing.state == "archived":
            if existing.is_contradicted:
                # The user explicitly re-asserted a previously contradicted
                # statement: it is the newest evidence, so reactivate it.
                existing.state = "active"
                existing.is_contradicted = False
                existing.contradicted_by_id = None
                bump_version(existing)
            else:
                # Archived merged duplicate: never resurrect it; let the
                # canonical memory be found through the semantic path.
                existing = None

        if existing:
            existing.importance = min(
                existing.importance + 0.05,
                1.0,
            )
            existing.access_count += 1
            existing.last_accessed = datetime.now(UTC)
            update_memory_state(existing)
            decay_memory(existing)
            return _persist(db_session, existing, commit)

        if embedding is None:
            embedding = generate_embedding(content)

        candidates = semantic_search(
            db=db_session,
            query=content,
            limit=5,
            query_embedding=embedding,
        ) if semantic_dedupe else []

        # semantic_search returns live memories only: archived (merged or
        # contradicted) memories must not absorb new evidence.

        duplicate = find_duplicate(candidates)

        if duplicate:
            duplicate = lock_memory(db_session, duplicate)
            strengthen_memory(duplicate)
            update_memory_state(duplicate)
            decay_memory(duplicate)
            return _persist(db_session, duplicate, commit)

        memory = Memory(
            content=content,
            category=category,
            importance=calculate_importance(category),
            embedding=embedding,
            state="active",
        )

        db_session.add(memory)
        return _persist(db_session, memory, commit)

    finally:
        if db is None:
            db_session.close()


def get_memories(
    category: str | None = None,
    min_importance: float | None = None,
    keyword: str | None = None,
    db: Session | None = None,
    record_access: bool = False,
):
    """
    List live memories.

    Administrative listing by default: it does NOT touch access_count,
    last_accessed or lifecycle state, so dashboards cannot artificially
    strengthen memories. Pass record_access=True only when the listing is a
    genuine cognitive retrieval of these memories.
    """
    db_session = db if db is not None else SessionLocal()

    try:
        query = (
            db_session.query(Memory)
            .filter(
                Memory.state != "archived"
            )
        )

        if category:
            query = query.filter(Memory.category == category)

        if min_importance is not None:
            query = query.filter(Memory.importance >= min_importance)

        if keyword:
            query = query.filter(Memory.content.ilike(f"%{keyword}%"))

        memories = query.order_by(desc(Memory.importance)).all()

        if record_access:
            for memory in memories:
                # Row lock: read-modify-write of counters/lifecycle state.
                memory = lock_memory(db_session, memory)
                memory.access_count += 1
                memory.last_accessed = datetime.now(UTC)
                update_memory_state(memory)
                decay_memory(memory)
            db_session.commit()

        return memories

    finally:
        if db is None:
            db_session.close()


def _get_or_404(db_session: Session, memory_id: int) -> Memory:
    memory = db_session.get(Memory, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return memory


def _admin_evidence(db_session: Session, memory: Memory, decision: str, provenance=None, **fields):
    from .provenance.models import DETERMINISTIC_NLP, EXTRACTOR_VERSION, MemoryEvidence, Provenance

    provenance = provenance or Provenance(source_type="admin")
    evidence = MemoryEvidence(
        memory_id=memory.id,
        source_type=provenance.source_type,
        conversation_id=provenance.conversation_id,
        message_id=provenance.message_id,
        extraction_method=fields.pop("extraction_method", DETERMINISTIC_NLP),
        extractor_version=fields.pop("extractor_version", EXTRACTOR_VERSION),
        decision=decision,
        **fields,
    )
    if provenance.observed_at is not None:
        evidence.observed_at = provenance.observed_at
    db_session.add(evidence)


def update_memory(
    memory_id: int,
    content: str,
    db: Session | None = None,
    expected_version: int | None = None,
    provenance=None,
):
    """
    Administrative correction of a memory's text (PUT /memory/{id}).

    This is deliberately NOT a knowledge-evolution event: it does not run the
    classifier, supersede or contradict other memories. It is an explicit
    edit with the same safety guarantees as evolution:
    - fact-domain locks (old and new fact) + row lock, optional optimistic
      check (expected_version -> 409 on mismatch), version bump;
    - embedding recomputed; lifecycle state and lineage left unchanged;
    - persistent graph links of the memory rebuilt from the new text;
    - evidence row with the new text and the previous text (append-only);
    - one transaction: all of it commits or none of it does.
    """
    from .graph.graph_service import GraphService
    from .knowledge.fact_extractor import extract_fact
    from .knowledge.fact_index import sync_memory_fact
    from .understanding.memory_parser import parse_memory

    db_session = db if db is not None else SessionLocal()

    try:
        memory = _get_or_404(db_session, memory_id)
        new_parsed = parse_memory(content)
        lock_fact_domains(
            db_session,
            [extract_fact(parse_memory(memory.content)), extract_fact(new_parsed)],
        )
        memory = lock_memory(db_session, memory)
        if expected_version is not None and memory.version != expected_version:
            raise HTTPException(
                status_code=409,
                detail=f"Memory {memory_id} is at version {memory.version}, expected {expected_version}.",
            )

        previous = memory.content
        memory.content = content
        memory.embedding = generate_embedding(content)
        memory.last_accessed = datetime.now(UTC)
        bump_version(memory)
        db_session.flush()

        # Shadow fact index follows the new content, in this transaction.
        sync_memory_fact(db_session, memory)

        graph = GraphService(db_session)
        graph.sql.unlink_memory(memory.id)
        graph.persist_memory(new_parsed, memory.id)
        graph.sql.delete_orphan_entities()

        fact = extract_fact(new_parsed)
        _admin_evidence(
            db_session, memory, "admin_update", provenance,
            confidence=fact.confidence if fact is not None else None,
            raw_text=content,
            previous_text=previous,
            reason_codes=["admin_update"],
        )
        db_session.commit()
        db_session.refresh(memory)

        compat = GraphService()
        compat.forget_memory(memory.id)
        compat.process_memory(new_parsed, memory.id)
        return memory

    except Exception:
        db_session.rollback()
        raise
    finally:
        if db is None:
            db_session.close()


def archive_memory(
    memory_id: int,
    db: Session | None = None,
    provenance=None,
):
    """
    Default DELETE /memory/{id}: lifecycle archival (reversible, non-destructive).

    The memory leaves normal retrieval ('archived'); its evidence, lineage and
    graph links are preserved, and an evidence row records the request.
    Idempotent for already-archived memories.
    """
    db_session = db if db is not None else SessionLocal()

    try:
        memory = lock_memory(db_session, _get_or_404(db_session, memory_id))
        if memory.state != "archived":
            memory.state = "archived"
            bump_version(memory)
            _admin_evidence(
                db_session, memory, "archived_by_request", provenance,
                extraction_method=None, extractor_version=None,
                reason_codes=["archived_by_request"],
            )
        db_session.commit()
        return {
            "message": "Memory archived. Use purge=true to delete it permanently.",
            "memory_id": memory_id,
            "mode": "archived",
        }
    except Exception:
        db_session.rollback()
        raise
    finally:
        if db is None:
            db_session.close()


def purge_memory(
    memory_id: int,
    db: Session | None = None,
):
    """
    Explicit, permanent administrative purge (DELETE /memory/{id}?purge=true).

    Destroys the memory, its evidence, its lineage rows and its graph links
    (FK cascades), then removes entities left without any memory or alias.
    Memories whose lineage pointed at the purged memory are kept; each gets
    an evidence row recording which link was removed, so the loss is
    auditable (e.g. a memory it had superseded is no longer HISTORICAL; a
    memory it had contradicted stays archived/contradicted, now with
    contradicted_by_id NULL).
    """
    from .graph.graph_service import GraphService

    db_session = db if db is not None else SessionLocal()

    try:
        memory = _get_or_404(db_session, memory_id)

        rels = db_session.query(MemoryRelationship).filter(
            (MemoryRelationship.source_memory_id == memory_id)
            | (MemoryRelationship.target_memory_id == memory_id)
        ).all()
        affected = {}
        for r in rels:
            other = r.target_memory_id if r.source_memory_id == memory_id else r.source_memory_id
            direction = "outgoing" if r.source_memory_id == other else "incoming"
            affected.setdefault(other, []).append(f"{r.relationship_type}:{direction}")
        for m in db_session.query(Memory).filter(Memory.contradicted_by_id == memory_id):
            affected.setdefault(m.id, []).append("contradicted_by:outgoing")

        # Lock everything touched, in id order.
        for mid in sorted(set(affected) | {memory_id}):
            db_session.query(Memory).filter(Memory.id == mid).with_for_update().one()

        for other_id, links in sorted(affected.items()):
            other = db_session.get(Memory, other_id)
            bump_version(other)
            _admin_evidence(
                db_session, other, "lineage_removed_by_purge", None,
                extraction_method=None, extractor_version=None,
                reason_codes=[f"purged_memory:{memory_id}"] + sorted(links),
            )

        db_session.delete(memory)
        db_session.flush()
        GraphService(db_session).sql.delete_orphan_entities()
        db_session.commit()

        GraphService().forget_memory(memory_id)
        return {
            "message": "Memory permanently purged.",
            "memory_id": memory_id,
            "mode": "purged",
            "affected_memory_ids": sorted(affected),
        }
    except Exception:
        db_session.rollback()
        raise
    finally:
        if db is None:
            db_session.close()


def delete_memory(
    memory_id: int,
    db: Session | None = None,
    purge: bool = False,
):
    """DELETE /memory/{id}: archive by default; permanent purge only when explicit."""
    if purge:
        return purge_memory(memory_id, db=db)
    return archive_memory(memory_id, db=db)


def reinforce_existing_memory(db: Session, memory: Memory, commit: bool = True):
    memory.importance = min(memory.importance + 0.05, 1.0)
    memory.access_count += 1
    memory.confidence = min(memory.confidence + 0.10, 1.0)
    memory.last_accessed = datetime.now(UTC)
    update_memory_state(memory)
    decay_memory(memory)
    return _persist(db, memory, commit)


def contradict_existing_memory(
    db: Session,
    existing_memory: Memory,
    new_memory_id: int,
    commit: bool = True,
):
    if existing_memory.id == new_memory_id:
        raise ValueError(f"memory {new_memory_id} cannot contradict itself")
    existing_memory.is_contradicted = True
    existing_memory.contradicted_by_id = new_memory_id
    existing_memory.confidence = max(existing_memory.confidence - 0.20, 0.0)
    existing_memory.state = "archived"
    bump_version(existing_memory)
    return _persist(db, existing_memory, commit)


def supersede_existing_fact_memory(
    db: Session,
    existing_memory: Memory,
    new_memory_id: int,
    commit: bool = True,
) -> Memory:
    """
    Mark an existing memory as superseded by a newer fact (SUPERSESSION workflow).
    Preserves existing memory in database with state='active' so it remains retrievable for historical queries.
    Links supersession relationship via MemoryRelationship table (relationship_type='superseded_by').
    Does NOT mark is_contradicted = True or overload contradicted_by_id.
    """
    existing_memory.is_contradicted = False
    existing_memory.contradicted_by_id = None
    existing_memory.state = "active"
    bump_version(existing_memory)
    db.flush()

    # Idempotent lineage link (unique constraint + ON CONFLICT DO NOTHING)
    lineage.link(db, existing_memory.id, new_memory_id, lineage.SUPERSEDED_BY)

    return _persist(db, existing_memory, commit)


def update_existing_fact_memory(
    db: Session,
    existing_memory: Memory,
    new_content: str,
    category: str | None = None,
    commit: bool = True,
) -> Memory:
    """
    Update an existing memory in place when a new memory updates an existing fact (UPDATE workflow).
    Prevents creating duplicate memory records.
    """
    existing_memory.content = new_content
    if category:
        existing_memory.category = category
    existing_memory.embedding = generate_embedding(new_content)
    existing_memory.last_accessed = datetime.now(UTC)
    existing_memory.access_count += 1
    existing_memory.is_contradicted = False
    existing_memory.contradicted_by_id = None
    existing_memory.confidence = min(existing_memory.confidence + 0.05, 1.0)
    update_memory_state(existing_memory)
    bump_version(existing_memory)
    return _persist(db, existing_memory, commit)


def merge_existing_memories(
    db: Session,
    existing_memories: list,
    merged_content: str,
    category: str,
    commit: bool = True,
    embedding: list[float] | None = None,
) -> Memory:
    """
    Consolidate equivalent memories into one canonical memory.

    Lineage is preserved: every archived duplicate gets a 'merged_into' link
    to the canonical memory, relationships are transferred, the earliest
    created_at is kept, and the original statements remain recoverable from
    the duplicates and from the evidence records (app/provenance).
    """
    cleaned_mems = []
    for item in existing_memories:
        m = get_memory_object(item)
        if hasattr(m, "id"):
            cleaned_mems.append(m)

    if not cleaned_mems:
        return create_memory(
            content=merged_content, category=category, db=db,
            embedding=embedding, commit=commit,
        )

    canonical = cleaned_mems[0]

    conf_values = [
        m.confidence
        for m in cleaned_mems
        if hasattr(m, "confidence") and m.confidence is not None
    ]
    preserved_conf = max(conf_values) if conf_values else 1.0

    timestamps = [
        m.created_at
        for m in cleaned_mems
        if getattr(m, "created_at", None) is not None
    ]
    earliest_created = min(timestamps) if timestamps else datetime.now(UTC)

    total_access = sum([getattr(m, "access_count", 0) for m in cleaned_mems]) + 1

    canonical.content = merged_content
    canonical.category = category
    canonical.embedding = embedding if embedding is not None else generate_embedding(merged_content)
    canonical.confidence = min(preserved_conf + 0.05, 1.0)
    canonical.access_count = total_access
    canonical.created_at = earliest_created
    canonical.last_accessed = datetime.now(UTC)
    canonical.state = "active"
    canonical.is_contradicted = False
    canonical.contradicted_by_id = None
    bump_version(canonical)

    canonical_id = canonical.id

    existing_rel_pairs = set()
    canonical_rels = db.query(MemoryRelationship).filter(
        (MemoryRelationship.source_memory_id == canonical_id)
        | (MemoryRelationship.target_memory_id == canonical_id)
    ).all()
    for r in canonical_rels:
        existing_rel_pairs.add(
            (r.source_memory_id, r.target_memory_id, r.relationship_type)
        )

    merged_ids = []
    for other_mem in cleaned_mems[1:]:
        if other_mem.id == canonical_id:
            continue
        other_mem.state = "archived"
        other_mem.is_contradicted = False
        other_mem.contradicted_by_id = None
        bump_version(other_mem)
        merged_ids.append(other_mem.id)

        other_rels = db.query(MemoryRelationship).filter(
            (MemoryRelationship.source_memory_id == other_mem.id)
            | (MemoryRelationship.target_memory_id == other_mem.id)
        ).all()

        for rel in other_rels:
            new_src = (
                canonical_id
                if rel.source_memory_id == other_mem.id
                else rel.source_memory_id
            )
            new_tgt = (
                canonical_id
                if rel.target_memory_id == other_mem.id
                else rel.target_memory_id
            )

            if new_src == new_tgt:
                db.delete(rel)
                continue

            pair_key = (new_src, new_tgt, rel.relationship_type)
            if pair_key in existing_rel_pairs:
                db.delete(rel)
            else:
                rel.source_memory_id = new_src
                rel.target_memory_id = new_tgt
                existing_rel_pairs.add(pair_key)

    db.flush()
    for merged_id in merged_ids:
        lineage.link(db, merged_id, canonical_id, lineage.MERGED_INTO)

    return _persist(db, canonical, commit)


def get_memory_evidence(memory_id: int, db: Session) -> dict:
    """Evidence records and lineage links for one memory (read-only)."""
    from .provenance.models import MemoryEvidence

    memory = db.get(Memory, memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found.")

    evidence = (
        db.query(MemoryEvidence)
        .filter(MemoryEvidence.memory_id == memory_id)
        .order_by(MemoryEvidence.observed_at, MemoryEvidence.id)
        .all()
    )
    rels = db.query(MemoryRelationship).filter(
        (MemoryRelationship.source_memory_id == memory_id)
        | (MemoryRelationship.target_memory_id == memory_id)
    ).all()
    other_ids = {r.source_memory_id for r in rels} | {r.target_memory_id for r in rels}
    if memory.contradicted_by_id:
        other_ids.add(memory.contradicted_by_id)
    others = {m.id: m for m in db.query(Memory).filter(Memory.id.in_(other_ids))} if other_ids else {}

    def link(relationship_type, other_id):
        return {
            "relationship_type": relationship_type,
            "memory_id": other_id,
            "content": others[other_id].content if other_id in others else "",
        }

    return {
        "memory": memory,
        "evidence": evidence,
        "outgoing": [link(r.relationship_type, r.target_memory_id) for r in rels if r.source_memory_id == memory_id],
        "incoming": [link(r.relationship_type, r.source_memory_id) for r in rels if r.target_memory_id == memory_id],
        "contradicted_by": link("contradicted_by", memory.contradicted_by_id) if memory.contradicted_by_id else None,
    }
