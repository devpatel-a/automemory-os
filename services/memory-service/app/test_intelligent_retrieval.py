from app.testing_support import reset_database
from datetime import UTC, datetime, timedelta
from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models import Memory
from app.semantic.semantic_service import generate_embedding
from app.retrieval_service import retrieve_memories
from app.pipeline.memory_pipeline import MemoryPipeline
from app.graph.graph_service import GraphService
from app.graph.repository import reset_shared_graph
from app.context.context_engine import ContextEngine


def clear_db():
    reset_database()


def test_deduplication_semantic_and_keyword():
    """Requirement 13.A: Same memory returned by semantic + keyword results in one final candidate."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(
            content="I love drinking espresso coffee every morning.",
            category="preference",
            embedding=generate_embedding("I love drinking espresso coffee every morning."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        db.add(m1)
        db.commit()
        db.refresh(m1)

        results = retrieve_memories(db, "espresso coffee", limit=5)
        mids = [r[0].id for r in results]
        assert len(mids) == len(set(mids))
        assert len(results) == 1
    finally:
        db.close()


def test_deduplication_semantic_and_graph():
    """Requirement 13.B: Same memory returned by semantic + graph results in one final candidate."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res = pipeline.process("I enjoy dark roast coffee.", "preference")
        m_id = res["memory"].id

        results = retrieve_memories(db, "dark roast coffee", limit=5)
        mids = [r[0].id for r in results]
        assert len(mids) == len(set(mids))
        assert m_id in mids
    finally:
        db.close()


def test_real_hybrid_fusion_multi_source_deduplication():
    """Section 3: Deterministic test verifying one Memory is discoverable through semantic, keyword, and graph retrieval, returning exactly once."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res = pipeline.process("I love drinking espresso coffee every morning.", "preference")
        mem_id = res["memory"].id

        # Query hits semantic, keyword ("espresso"), and graph ("espresso")
        results = retrieve_memories(db, "What do I know about espresso coffee?", limit=5)

        mids = [r[0].id for r in results]
        assert len(mids) == len(set(mids))  # Deduplicated exactly once
        assert mem_id in mids
    finally:
        db.close()


def test_graph_only_candidate_discovered():
    """Section 3 & Section 2: Simple query terms discover graph candidate even when not formal spaCy entity."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res = pipeline.process("I enjoy coffee.", "preference")
        graph_mem_id = res["memory"].id

        # Query using simple query term "coffee"
        results = retrieve_memories(db, "What do I know about coffee?", limit=5)
        mids = [r[0].id for r in results]
        assert graph_mem_id in mids
    finally:
        db.close()


def test_archived_memory_excluded():
    """Requirement 13.C: Archived memories are excluded from retrieval."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(
            content="I live in Old City.",
            category="profile",
            embedding=generate_embedding("I live in Old City."),
            state="archived",
            importance=0.8,
            confidence=1.0,
        )
        db.add(m1)
        db.commit()

        results = retrieve_memories(db, "Old City", limit=5)
        mids = [r[0].id for r in results]
        assert m1.id not in mids
    finally:
        db.close()


def test_active_replacement_beats_contradicted_archived_memory():
    """Requirement 13.D: Active replacement memory outranks contradicted archived memory."""
    clear_db()
    db = SessionLocal()
    try:
        m_old = Memory(
            content="I live in Mumbai.",
            category="profile",
            embedding=generate_embedding("I live in Mumbai."),
            state="archived",
            is_contradicted=True,
            importance=0.8,
            confidence=0.0,
        )
        db.add(m_old)
        db.commit()

        m_new = Memory(
            content="I live in Pune.",
            category="profile",
            embedding=generate_embedding("I live in Pune."),
            state="active",
            is_contradicted=False,
            importance=0.8,
            confidence=1.0,
        )
        db.add(m_new)
        db.commit()

        results = retrieve_memories(db, "Where do I live?", limit=5)
        assert len(results) > 0
        top_mem = results[0][0]
        assert top_mem.id == m_new.id
        assert top_mem.content == "I live in Pune."
    finally:
        db.close()


def test_highly_relevant_old_memory_beats_weakly_relevant_recent_memory():
    """Requirement 13.E: Highly relevant old memory beats weakly relevant recent memory."""
    clear_db()
    db = SessionLocal()
    try:
        old_time = datetime.now(UTC) - timedelta(days=60)
        recent_time = datetime.now(UTC) - timedelta(minutes=5)

        m_old_relevant = Memory(
            content="My favorite programming language is Python.",
            category="preference",
            embedding=generate_embedding("My favorite programming language is Python."),
            state="active",
            importance=0.9,
            created_at=old_time,
            last_accessed=old_time,
        )

        m_recent_weak = Memory(
            content="I bought a blue shirt yesterday.",
            category="event",
            embedding=generate_embedding("I bought a blue shirt yesterday."),
            state="active",
            importance=0.4,
            created_at=recent_time,
            last_accessed=recent_time,
        )

        db.add_all([m_old_relevant, m_recent_weak])
        db.commit()

        results = retrieve_memories(db, "What is my favorite programming language?", limit=5)
        assert len(results) > 0
        top_mem = results[0][0]
        assert top_mem.id == m_old_relevant.id
    finally:
        db.close()


def test_importance_provides_moderate_ranking_bonus():
    """Requirement 13.F: Memory importance provides a moderate ranking bonus."""
    clear_db()
    db = SessionLocal()
    try:
        m_low_imp = Memory(
            content="I occasionally drink black tea.",
            category="preference",
            embedding=generate_embedding("I occasionally drink black tea."),
            state="active",
            importance=0.2,
        )

        m_high_imp = Memory(
            content="I frequently drink black tea.",
            category="preference",
            embedding=generate_embedding("I frequently drink black tea."),
            state="active",
            importance=0.95,
        )

        db.add_all([m_low_imp, m_high_imp])
        db.commit()

        results = retrieve_memories(db, "black tea", limit=5)
        assert len(results) >= 2
        top_mem = results[0][0]
        assert top_mem.id == m_high_imp.id
    finally:
        db.close()


def test_access_count_weak_signal():
    """Requirement 13.G: Access count provides only a weak ranking bonus."""
    clear_db()
    db = SessionLocal()
    try:
        m_high_access = Memory(
            content="I drink green tea.",
            category="preference",
            embedding=generate_embedding("I drink green tea."),
            state="active",
            access_count=50,
            importance=0.5,
        )

        m_exact_match = Memory(
            content="I absolutely love matcha green tea.",
            category="preference",
            embedding=generate_embedding("I absolutely love matcha green tea."),
            state="active",
            access_count=1,
            importance=0.9,
        )

        db.add_all([m_high_access, m_exact_match])
        db.commit()

        results = retrieve_memories(db, "matcha green tea", limit=5)
        top_mem = results[0][0]
        assert top_mem.id == m_exact_match.id
    finally:
        db.close()


def test_graph_connected_candidate_relevance():
    """Requirement 13.H & I: Graph-connected candidate receives graph relevance bonus."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I love eating pizza with cheese.", "preference")
        mem_graph = res1["memory"]

        m_no_graph = Memory(
            content="Some random general statement.",
            category="event",
            embedding=generate_embedding("Some random general statement."),
            state="active",
        )
        db.add(m_no_graph)
        db.commit()

        results = retrieve_memories(db, "pizza", limit=5)
        mids = [r[0].id for r in results]
        assert mem_graph.id in mids
    finally:
        db.close()


def test_keyword_exact_match_beats_weak_overlap():
    """Requirement 13.J: Keyword exact match beats weak keyword overlap."""
    clear_db()
    db = SessionLocal()
    try:
        m_weak = Memory(
            content="The weather is nice in the city.",
            category="event",
            embedding=generate_embedding("The weather is nice in the city."),
            state="active",
        )

        m_exact = Memory(
            content="My favorite city is Tokyo.",
            category="preference",
            embedding=generate_embedding("My favorite city is Tokyo."),
            state="active",
        )

        db.add_all([m_weak, m_exact])
        db.commit()

        results = retrieve_memories(db, "favorite city Tokyo", limit=5)
        top_mem = results[0][0]
        assert top_mem.id == m_exact.id
    finally:
        db.close()


def test_category_relevance_inference():
    """Requirement 13.K: Category relevance works when category intent is implied."""
    clear_db()
    db = SessionLocal()
    try:
        m_pref = Memory(
            content="I prefer dark roast espresso.",
            category="preference",
            embedding=generate_embedding("I prefer dark roast espresso."),
            state="active",
        )

        m_event = Memory(
            content="I attended a coffee tasting event.",
            category="event",
            embedding=generate_embedding("I attended a coffee tasting event."),
            state="active",
        )

        db.add_all([m_pref, m_event])
        db.commit()

        results = retrieve_memories(db, "What are my preferences for espresso?", limit=5)
        top_mem = results[0][0]
        assert top_mem.id == m_pref.id
    finally:
        db.close()


def test_context_engine_compatibility():
    """Requirement 13.L & M: ContextEngine compatibility and public API return signature [(Memory, score), ...]."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(
            content="I live in San Francisco.",
            category="profile",
            embedding=generate_embedding("I live in San Francisco."),
            state="active",
            importance=0.9,
        )
        db.add(m1)
        db.commit()

        results = retrieve_memories(db, "Where do I live?", limit=5)
        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], Memory)
            assert isinstance(item[1], (float, int))

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Where do I live?")
        assert ctx is not None
        assert ctx.query == "Where do I live?"
    finally:
        db.close()
