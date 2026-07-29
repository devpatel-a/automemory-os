from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import desc

from .database import SessionLocal
from .models import Memory


def calculate_importance(category: str) -> float:
    scores = {
        "profile": 0.95,
        "preference": 0.80,
        "habit": 0.70,
        "event": 0.50,
    }

    return scores.get(category.lower(), 0.40)


def update_memory_state(memory):
    if memory.access_count >= 3:
        memory.state = "active"
    else:
        memory.state = "weak"


def create_memory(content: str, category: str):
    db = SessionLocal()

    try:
        existing_memory = (
            db.query(Memory)
            .filter(Memory.content == content)
            .first()
        )

        if existing_memory:
            existing_memory.importance = min(
                existing_memory.importance + 0.05,
                1.0,
            )

            existing_memory.access_count += 1
            existing_memory.last_accessed = datetime.now(UTC)

            db.commit()
            db.refresh(existing_memory)

            return existing_memory

        importance = calculate_importance(category)

        memory = Memory(
            content=content,
            category=category,
            importance=importance,
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
        query = db.query(Memory)

        if category:
            query = query.filter(
                Memory.category == category
            )

        if min_importance is not None:
            query = query.filter(
                Memory.importance >= min_importance
            )

        if keyword:
            query = query.filter(
                Memory.content.ilike(f"%{keyword}%")
            )

        memories = (
            query
            .order_by(desc(Memory.importance))
            .all()
        )

        for memory in memories:
            memory.access_count += 1
            memory.last_accessed = datetime.now(UTC)
            update_memory_state(memory)

        db.commit()

        return memories

    finally:
        db.close()


def update_memory(memory_id: int, content: str):
    db = SessionLocal()

    try:
        memory = (
            db.query(Memory)
            .filter(Memory.id == memory_id)
            .first()
        )

        if memory is None:
            raise HTTPException(
                status_code=404,
                detail="Memory not found.",
            )

        memory.content = content
        memory.last_accessed = datetime.now(UTC)

        db.commit()
        db.refresh(memory)

        return memory

    finally:
        db.close()


def delete_memory(memory_id: int):
    db = SessionLocal()

    try:
        memory = (
            db.query(Memory)
            .filter(Memory.id == memory_id)
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