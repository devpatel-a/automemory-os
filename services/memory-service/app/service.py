from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import desc

from .database import SessionLocal
from .models import Memory

from .semantic.semantic_service import (
    generate_embedding,
    semantic_search,
)

from .duplicate_service import (
    find_duplicate,
    strengthen_memory,
)


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
):
    """
    Store or reinforce a memory.

    This function is intentionally responsible
    only for persistence-related logic.

    Workflow orchestration belongs to
    MemoryPipeline.
    """

    db = SessionLocal()

    try:

        existing = (
            db.query(Memory)
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

            existing.last_accessed = datetime.now(
                UTC
            )

            update_memory_state(existing)

            decay_memory(existing)

            db.commit()

            db.refresh(existing)

            return existing

        embedding = generate_embedding(
            content
        )

        candidates = semantic_search(
            db=db,
            query=content,
            limit=5,
        )

        duplicate = find_duplicate(
            candidates
        )

        if duplicate:

            strengthen_memory(
                duplicate
            )

            update_memory_state(
                duplicate
            )

            decay_memory(
                duplicate
            )

            db.commit()

            db.refresh(
                duplicate
            )

            return duplicate

        memory = Memory(

            content=content,

            category=category,

            importance=calculate_importance(
                category
            ),

            embedding=embedding,

            state="active",
        )

        db.add(memory)

        db.commit()

        db.refresh(memory)

        return memory

    finally:

        db.close()


def get_memories(
    category: str | None = None,
    min_importance: float | None = None,
    keyword: str | None = None,
):
    db = SessionLocal()

    try:

        query = (
            db.query(Memory)
            .filter(
                Memory.state != "archived"
            )
        )

        if category:

            query = query.filter(
                Memory.category == category
            )

        if min_importance is not None:

            query = query.filter(
                Memory.importance
                >= min_importance
            )

        if keyword:

            query = query.filter(
                Memory.content.ilike(
                    f"%{keyword}%"
                )
            )

        memories = (
            query.order_by(
                desc(
                    Memory.importance
                )
            ).all()
        )

        for memory in memories:

            memory.access_count += 1

            memory.last_accessed = datetime.now(
                UTC
            )

            update_memory_state(
                memory
            )

            decay_memory(
                memory
            )

        db.commit()

        return memories

    finally:

        db.close()


def update_memory(
    memory_id: int,
    content: str,
):
    db = SessionLocal()

    try:

        memory = (
            db.query(Memory)
            .filter(
                Memory.id == memory_id
            )
            .first()
        )

        if memory is None:

            raise HTTPException(
                status_code=404,
                detail="Memory not found.",
            )

        memory.content = content

        memory.embedding = generate_embedding(
            content
        )

        memory.last_accessed = datetime.now(
            UTC
        )

        db.commit()

        db.refresh(memory)

        return memory

    finally:

        db.close()


def delete_memory(
    memory_id: int,
):
    db = SessionLocal()

    try:

        memory = (
            db.query(Memory)
            .filter(
                Memory.id == memory_id
            )
            .first()
        )

        if memory is None:

            raise HTTPException(
                status_code=404,
                detail="Memory not found.",
            )

        db.delete(memory)

        db.commit()

        return {
            "message": "Memory deleted successfully."
        }

    finally:

        db.close()


def reinforce_existing_memory(db, memory: Memory):
    memory.importance = min(memory.importance + 0.05, 1.0)
    memory.access_count += 1
    memory.confidence = min(memory.confidence + 0.10, 1.0)
    memory.last_accessed = datetime.now(UTC)
    update_memory_state(memory)
    decay_memory(memory)
    db.commit()
    db.refresh(memory)
    return memory


def contradict_existing_memory(db, existing_memory: Memory, new_memory_id: int):
    existing_memory.is_contradicted = True
    existing_memory.contradicted_by_id = new_memory_id
    existing_memory.confidence = max(existing_memory.confidence - 0.20, 0.0)
    existing_memory.state = "archived"
    db.commit()
    db.refresh(existing_memory)
    return existing_memory


def merge_existing_memories(db, memory_ids: list[int], merged_content: str, category: str):
    merged_embedding = generate_embedding(merged_content)
    new_memory = Memory(
        content=merged_content,
        category=category,
        importance=calculate_importance(category),
        embedding=merged_embedding,
        state="active",
        confidence=1.0,
    )
    db.add(new_memory)
    db.flush()

    for mid in memory_ids:
        mem = db.query(Memory).filter(Memory.id == mid).first()
        if mem:
            mem.state = "archived"
            mem.is_contradicted = True
            mem.contradicted_by_id = new_memory.id

    db.commit()
    db.refresh(new_memory)
    return new_memory