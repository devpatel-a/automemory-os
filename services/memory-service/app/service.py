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


def create_memory(content: str, category: str):
    db = SessionLocal()

    try:
        importance = calculate_importance(category)

        memory = Memory(
            content=content,
            category=category,
            importance=importance,
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
            query = query.filter(Memory.category == category)

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
            return {"error": "Memory not found."}

        memory.content = content

        db.commit()
        db.refresh(memory)

        return {
            "message": "Memory updated successfully.",
            "memory": memory,
        }

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
            return {"error": "Memory not found."}

        db.delete(memory)
        db.commit()

        return {
            "message": "Memory deleted successfully."
        }

    finally:
        db.close()