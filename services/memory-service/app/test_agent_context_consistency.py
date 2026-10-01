"""
The agent's memories_used must be exactly the evidence of the final
ContextPackage used to build its prompt (single source of truth).
"""

from app.agent_service import MemoryAgent
from app.context.context_engine import ContextEngine
from app.database import SessionLocal
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.reflection_service import ReflectionEngine
from app.testing_support import reset_database


def seed(db):
    pipeline = MemoryPipeline(db)
    for statement, category in [
        ("I live in Mumbai.", "profile"),
        ("I moved to Pune.", "profile"),
        ("I will move to Bangalore next month.", "profile"),
        ("I like coffee.", "preference"),
        ("I work at BMW.", "profile"),
    ]:
        pipeline.process(statement, category)


def test_agent_memories_used_equal_context_evidence():
    reset_database()
    db = SessionLocal()
    try:
        seed(db)
        for query, top_k in [("Where do I live?", 5), ("Where did I live before?", 2), ("What do I like?", 3)]:
            package = ContextEngine().build_context(db, query, limit=top_k)
            expected_ids = [e.memory_id for e in package.evidence]

            result = MemoryAgent(db).query(query, top_k=top_k)
            used_ids = [m.id for m in result["memories_used"]]

            assert used_ids == expected_ids, query
            assert len(used_ids) <= top_k
            for memory in result["memories_used"]:
                assert memory.content in result["prompt"]
    finally:
        db.close()


def test_current_question_never_hands_the_agent_a_future_plan():
    reset_database()
    db = SessionLocal()
    try:
        seed(db)
        result = MemoryAgent(db).query("Where do I live?", top_k=5)
        contents = [m.content for m in result["memories_used"]]
        assert "I moved to Pune." in contents
        assert "I will move to Bangalore next month." not in contents
    finally:
        db.close()


def test_reflection_never_marks_memories_contradicted_from_generated_text():
    reset_database()
    db = SessionLocal()
    try:
        memory = Memory(content="I live in Pune.", category="profile", state="active")
        db.add(memory)
        db.commit()
        result = ReflectionEngine().reflect(
            db=db, query="Where do I live?",
            response="I live in Mumbai.",  # conflicting generated text
            memories_used=[memory],
        )
        db.refresh(memory)
        assert result["contradiction_detected"] is True
        assert result["conflicting_memory_ids"] == [memory.id]
        assert memory.is_contradicted is False
        assert memory.state == "active"
    finally:
        db.close()
