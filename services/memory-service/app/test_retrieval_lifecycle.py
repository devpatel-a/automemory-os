"""
Lifecycle-aware retrieval: filtering is enforced at the retrieval source,
and historical/future semantics are preserved on top of it.
"""

from sqlalchemy import text

from app.database import SessionLocal
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.retrieval_service import retrieve_memories
from app.semantic.semantic_service import generate_embedding, semantic_search
from app.context.context_engine import ContextEngine
from app.testing_support import reset_database


def add(db, content, state="active", **extra):
    memory = Memory(
        content=content, category="profile", state=state,
        embedding=generate_embedding(content), **extra,
    )
    db.add(memory)
    db.commit()
    return memory


def ids(results):
    return {m.id for m, _ in results}


def test_semantic_search_lifecycle_scopes():
    reset_database()
    db = SessionLocal()
    try:
        active = add(db, "I live in Pune.")
        weak = add(db, "I live in Pune city.", state="weak")
        archived = add(db, "I live in Mumbai.", state="archived", is_contradicted=True)

        live = ids(semantic_search(db, "Where do I live?", limit=10))
        assert active.id in live
        assert weak.id in live
        assert archived.id not in live

        everything = ids(semantic_search(db, "Where do I live?", limit=10, include_archived=True))
        assert archived.id in everything
    finally:
        db.close()


def test_hybrid_retrieval_excludes_archived_contradictions_by_default():
    reset_database()
    db = SessionLocal()
    try:
        active = add(db, "I live in Pune.")
        weak = add(db, "I live near Pune station.", state="weak")
        archived = add(db, "I live in Mumbai.", state="archived", is_contradicted=True)

        normal = ids(retrieve_memories(db, "Where do I live?", limit=10))
        assert {active.id, weak.id} <= normal
        assert archived.id not in normal

        historical = ids(retrieve_memories(db, "Where do I live?", limit=10, include_archived=True))
        assert archived.id in historical
    finally:
        db.close()


def test_superseded_memory_available_to_historical_query_and_future_excluded_from_current():
    reset_database()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I moved to Pune.", "profile")
        pipeline.process("I will move to Bangalore next month.", "profile")

        engine = ContextEngine()
        historical = [e.content for e in engine.build_context(db, "Where did I live before?").evidence]
        assert "I live in Mumbai." in historical

        current = [e.content for e in engine.build_context(db, "Where do I live?").evidence]
        assert current[0] == "I moved to Pune."
        assert "I will move to Bangalore next month." not in current
    finally:
        db.close()


def test_evolution_candidates_exclude_archived_memories():
    """A contradicted (archived) claim must not be an evolution candidate."""
    reset_database()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I live in Pune.", "profile")
        archived = db.query(Memory).filter(Memory.content == "I live in Mumbai.").one()
        assert archived.state == "archived"

        candidates = semantic_search(db, "I live in Chennai.", limit=5)
        assert archived.id not in ids(candidates)
    finally:
        db.close()


def test_memories_without_embeddings_stay_reachable_with_index_scans_preferred():
    """Regression: an HNSW index (briefly added) skips NULL embeddings, so when the
    planner used it, embedding-less memories vanished from semantic search."""
    reset_database()
    db = SessionLocal()
    try:
        db.add(Memory(content="I am vegetarian.", category="habit", state="active"))
        for i in range(30):
            add(db, f"Unrelated statement number {i}.")
        db.commit()
        db.execute(text("SET LOCAL enable_seqscan = off"))
        contents = [m.content for m, _ in semantic_search(db, "eating habits", limit=100)]
        assert "I am vegetarian." in contents
    finally:
        db.rollback()
        db.close()
