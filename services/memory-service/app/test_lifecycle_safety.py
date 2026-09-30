from app.testing_support import reset_database
"""
Lifecycle safety regressions: archiving must be an explicit evolution decision
(merge / contradiction), never a side effect of reinforcement or access decay.
"""

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import Memory
from app.graph.repository import reset_shared_graph
from app.pipeline.memory_pipeline import MemoryPipeline
from app.service import decay_memory, update_memory_state


def clear_db():
    reset_database()


def test_decay_never_archives():
    memory = Memory(content="x", category="fact", importance=0.1, access_count=0, state="active")
    decay_memory(memory)
    assert memory.state == "weak"


def test_access_counting_never_unarchives():
    memory = Memory(content="x", category="fact", importance=0.9, access_count=10, state="archived")
    update_memory_state(memory)
    assert memory.state == "archived"


def test_reinforcing_low_importance_fact_keeps_it_retrievable():
    """Regression: the API's default 'fact' category (importance 0.40) used to be
    archived by decay on its first reinforcement, making the fact disappear."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Pune.", "fact")
        pipeline.process("I live in Pune.", "fact")

        rows = db.query(Memory).filter(Memory.content == "I live in Pune.").all()
        assert len(rows) == 1
        assert rows[0].state != "archived"
        assert rows[0].is_contradicted is False
    finally:
        db.close()


def test_reasserting_contradicted_fact_reactivates_it():
    """Regression: Mumbai -> Pune -> Mumbai (all 'I live in X') used to archive BOTH
    memories, leaving no current residence at all."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I live in Pune.", "profile")
        pipeline.process("I live in Mumbai.", "profile")
        db.expire_all()

        mumbai = db.query(Memory).filter(Memory.content == "I live in Mumbai.").all()
        pune = db.query(Memory).filter(Memory.content == "I live in Pune.").one()

        assert len(mumbai) == 1
        # Retrievable again ('weak' is a retrievable lifecycle state).
        assert mumbai[0].state in ("active", "weak")
        assert mumbai[0].is_contradicted is False

        assert pune.state == "archived"
        assert pune.is_contradicted is True
        assert pune.contradicted_by_id == mumbai[0].id
    finally:
        db.close()


def test_memory_is_never_contradicted_by_itself():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I live in Pune.", "profile")
        pipeline.process("I live in Mumbai.", "profile")
        db.expire_all()
        for memory in db.query(Memory).all():
            assert memory.contradicted_by_id != memory.id
    finally:
        db.close()
