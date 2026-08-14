from app.database import SessionLocal, engine
from sqlalchemy import text
from app.pipeline.memory_pipeline import MemoryPipeline
from app.service import create_memory, update_existing_fact_memory
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
        initial_mem = res1["memory"]

        # Direct in-place fact update execution
        updated_mem = update_existing_fact_memory(
            db=db,
            existing_memory=initial_mem,
            new_content="I work at Google DeepMind.",
            category="profile",
        )

        assert updated_mem.id == initial_mem.id
        assert updated_mem.content == "I work at Google DeepMind."
        assert updated_mem.is_contradicted is False
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
