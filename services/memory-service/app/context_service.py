from sqlalchemy import desc

from .database import SessionLocal
from .models import Memory


def build_context(
    query: str | None = None,
    top_k: int = 5,
):
    db = SessionLocal()

    try:
        memories = (
            db.query(Memory)
            .filter(Memory.state != "archived")
        )

        if query:
            memories = memories.filter(
                Memory.content.ilike(f"%{query}%")
            )

        memories = (
            memories
            .order_by(desc(Memory.importance))
            .limit(top_k)
            .all()
        )

        return memories

    finally:
        db.close()