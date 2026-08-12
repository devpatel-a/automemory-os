from app.database import SessionLocal, engine
from sqlalchemy import text
from app.pipeline.memory_pipeline import MemoryPipeline
from app.service import create_memory
from app.relationship_service import create_relationship, get_related_memories
from app.decision.decision_types import MemoryAction


def clear_db():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM memory_relationships;"))
        conn.execute(text("DELETE FROM memories;"))
        conn.commit()


def test_memory_evolution_update_workflow():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Initial fact
        res1 = pipeline.process(
            content="I work at Google.",
            category="profile",
        )
        initial_id = res1["memory"].id

        # Superseding fact (UPDATE workflow)
        res2 = pipeline.process(
            content="I work at Apple.",
            category="profile",
        )

        assert res2["decision"].action == MemoryAction.UPDATE
        assert res2["memory"].id == initial_id
        assert res2["memory"].content == "I work at Apple."
        assert res2["memory"].is_contradicted is False
    finally:
        db.close()


def test_memory_evolution_merge_workflow():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Create two semantically equivalent memories
        m1 = create_memory("I enjoy espresso coffee.", "preference")
        m2 = create_memory("I love drinking espresso.", "preference")
        create_relationship(db, m1.id, m2.id, "related_to")

        # Process merge
        res = pipeline.process(
            content="I love drinking espresso coffee.",
            category="preference",
        )

        merged_mem = res["memory"]
        assert merged_mem is not None
        assert hasattr(merged_mem, "confidence")
        assert merged_mem.confidence >= 0.90
        assert merged_mem.created_at is not None
    finally:
        db.close()
