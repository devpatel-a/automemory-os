"""
Retrieval exposes independently measurable signals per candidate, and the
context evidence carries them through to the final package.
"""

from app.context.context_engine import ContextEngine
from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline
from app.retrieval_service import retrieve_candidates, retrieve_memories
from app.testing_support import reset_database


def seed(db):
    pipeline = MemoryPipeline(db)
    pipeline.process("My friend Rahul works at Google.", "fact")
    pipeline.process("I live in Pune.", "profile")
    pipeline.process("I like tea.", "preference")


def test_candidates_expose_separate_signals_and_reasons():
    reset_database()
    db = SessionLocal()
    try:
        seed(db)
        candidates = retrieve_candidates(db, "Where does Rahul work?", limit=5)
        top = candidates[0]
        assert top.memory.content == "My friend Rahul works at Google."
        assert top.memory_id == top.memory.id
        assert top.semantic_score is not None and 0.0 <= top.semantic_score <= 1.0
        assert top.graph_score == 1.0
        assert "graph_entity_match" in top.reasons and "semantic_match" in top.reasons
        assert top.lifecycle_state == "active"
        assert top.confidence is not None
        # context-stage signals are not measured at retrieval
        assert top.attribute_score is None and top.temporal_score is None
    finally:
        db.close()


def test_retrieve_memories_is_backward_compatible():
    reset_database()
    db = SessionLocal()
    try:
        seed(db)
        legacy = retrieve_memories(db, "Where do I live?", limit=3)
        structured = retrieve_candidates(db, "Where do I live?", limit=3)
        assert [m.id for m, _ in legacy] == [c.memory_id for c in structured]
        # recency is time-dependent, so scores from two calls differ by ~1e-9
        for (_, score), candidate in zip(legacy, structured):
            assert abs(score - candidate.final_score) < 1e-6
    finally:
        db.close()


def test_context_evidence_carries_all_signals():
    reset_database()
    db = SessionLocal()
    try:
        seed(db)
        package = ContextEngine().build_context(db, "What city do I live in?")
        top = package.evidence[0]
        assert top.content == "I live in Pune."
        expected = {"semantic", "lexical", "graph", "entity", "attribute", "temporal", "relationship", "final"}
        assert expected <= set(top.signals)
        assert top.signals["attribute"] > 0          # residence attribute matched
        assert top.signals["temporal"] > 0           # CURRENT aligned with CURRENT intent
        assert top.signals["relationship"] is None   # not measured yet, explicitly
        assert top.signals["final"] == top.score
    finally:
        db.close()
