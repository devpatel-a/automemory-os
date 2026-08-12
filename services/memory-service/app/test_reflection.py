from app.database import SessionLocal
from app.reflection_service import ReflectionEngine
from app.models import Memory


def test_reflection_engine():
    db = SessionLocal()
    try:
        engine = ReflectionEngine()
        mem = Memory(content="I live in Pune.", category="profile")
        db.add(mem)
        db.commit()
        db.refresh(mem)

        result = engine.reflect(
            db=db,
            query="Where do I live?",
            response="You live in Pune.",
            memories_used=[mem],
        )

        assert result["reflection_status"] == "completed"
        assert mem.id in result["accessed_memory_ids"]
        assert mem.access_count >= 1
    finally:
        db.close()
