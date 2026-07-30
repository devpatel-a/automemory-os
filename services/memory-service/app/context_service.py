from sqlalchemy import desc

from .database import SessionLocal
from .models import Memory


def build_context(top_k: int = 5):
    db = SessionLocal()

    try:
        memories = (
            db.query(Memory)
            .filter(Memory.state != "archived")
            .order_by(desc(Memory.importance))
            .limit(top_k)
            .all()
        )

        return memories

    finally:
        db.close()