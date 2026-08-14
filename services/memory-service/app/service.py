from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from .database import SessionLocal
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
    if memory.access_count >= 3:
        memory.state = "active"
    else:
        memory.state = "weak"


def decay_memory(memory: Memory):
    if (
        memory.importance < 0.5
        and memory.access_count < 3
    ):
        memory.state = "archived"


def create_memory(
    content: str,
    category: str,
    db: Session | None = None,
):
    """
    Store or reinforce a memory with optional database session reuse.
    """
    db_session = db if db is not None else SessionLocal()

    try:
        existing = (
            db_session.query(Memory)
            .filter(
                Memory.content == content
            )
            .first()
        )

        if existing:
            existing.importance = min(
                existing.importance + 0.05,
                1.0,
            )
            existing.access_count += 1
            existing.last_accessed = datetime.now(UTC)
            update_memory_state(existing)
            decay_memory(existing)
            db_session.commit()
            db_session.refresh(existing)
            return existing

        embedding = generate_embedding(content)

        candidates = semantic_search(
            db=db_session,
            query=content,
            limit=5,
        )

        duplicate = find_duplicate(candidates)

        if duplicate:
            strengthen_memory(duplicate)
            update_memory_state(duplicate)
            decay_memory(duplicate)
            db_session.commit()
            db_session.refresh(duplicate)
            return duplicate

        memory = Memory(
            content=content,
            category=category,
            importance=calculate_importance(category),
            embedding=embedding,
            state="active",
        )

        db_session.add(memory)
        db_session.commit()
        db_session.refresh(memory)
        return memory

    finally:
        if db is None:
            db_session.close()


def get_memories(
    category: str | None = None,
    min_importance: float | None = None,
    keyword: str | None = None,
    db: Session | None = None,
):
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

        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = datetime.now(UTC)
            update_memory_state(memory)
            decay_memory(memory)

        db_session.commit()
        return memories

    finally:
        if db is None:
            db_session.close()


def update_memory(
    memory_id: int,
    content: str,
    db: Session | None = None,
):
    db_session = db if db is not None else SessionLocal()

    try:
        memory = (
            db_session.query(Memory)
            .filter(Memory.id == memory_id)
            .first()
        )

        if memory is None:
            raise HTTPException(
                status_code=404,
                detail="Memory not found.",
            )

        memory.content = content
        memory.embedding = generate_embedding(content)
        memory.last_accessed = datetime.now(UTC)
        db_session.commit()
        db_session.refresh(memory)
        return memory

    finally:
        if db is None:
            db_session.close()


def delete_memory(
    memory_id: int,
    db: Session | None = None,
):
    db_session = db if db is not None else SessionLocal()

    try:
        memory = (
            db_session.query(Memory)
            .filter(Memory.id == memory_id)
            .first()
        )

        if memory is None:
            raise HTTPException(
                status_code=404,
                detail="Memory not found.",
            )

        db_session.delete(memory)
        db_session.commit()
        return {"message": "Memory deleted successfully."}

    finally:
        if db is None:
            db_session.close()


def reinforce_existing_memory(db: Session, memory: Memory):
    memory.importance = min(memory.importance + 0.05, 1.0)
    memory.access_count += 1
    memory.confidence = min(memory.confidence + 0.10, 1.0)
    memory.last_accessed = datetime.now(UTC)
    update_memory_state(memory)
    decay_memory(memory)
    db.commit()
    db.refresh(memory)
    return memory


def contradict_existing_memory(db: Session, existing_memory: Memory, new_memory_id: int):
    existing_memory.is_contradicted = True
    existing_memory.contradicted_by_id = new_memory_id
    existing_memory.confidence = max(existing_memory.confidence - 0.20, 0.0)
    existing_memory.state = "archived"
    db.commit()
    db.refresh(existing_memory)
    return existing_memory


def supersede_existing_fact_memory(
    db: Session,
    existing_memory: Memory,
    new_memory_id: int,
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

    # Link lineage via existing MemoryRelationship table
    existing_rel = (
        db.query(MemoryRelationship)
        .filter(
            MemoryRelationship.source_memory_id == existing_memory.id,
            MemoryRelationship.target_memory_id == new_memory_id,
            MemoryRelationship.relationship_type == "superseded_by",
        )
        .first()
    )
    if not existing_rel:
        rel = MemoryRelationship(
            source_memory_id=existing_memory.id,
            target_memory_id=new_memory_id,
            relationship_type="superseded_by",
        )
        db.add(rel)

    db.commit()
    db.refresh(existing_memory)
    return existing_memory


def update_existing_fact_memory(
    db: Session,
    existing_memory: Memory,
    new_content: str,
    category: str | None = None,
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
    db.commit()
    db.refresh(existing_memory)
    return existing_memory


def merge_existing_memories(
    db: Session,
    existing_memories: list,
    merged_content: str,
    category: str,
) -> Memory:
    cleaned_mems = []
    for item in existing_memories:
        m = get_memory_object(item)
        if hasattr(m, "id"):
            cleaned_mems.append(m)

    if not cleaned_mems:
        return create_memory(content=merged_content, category=category, db=db)

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
    canonical.embedding = generate_embedding(merged_content)
    canonical.confidence = min(preserved_conf + 0.05, 1.0)
    canonical.access_count = total_access
    canonical.created_at = earliest_created
    canonical.last_accessed = datetime.now(UTC)
    canonical.state = "active"
    canonical.is_contradicted = False
    canonical.contradicted_by_id = None

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

    for other_mem in cleaned_mems[1:]:
        if other_mem.id == canonical_id:
            continue
        other_mem.state = "archived"
        other_mem.is_contradicted = False
        other_mem.contradicted_by_id = None

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

    db.commit()
    db.refresh(canonical)
    return canonical