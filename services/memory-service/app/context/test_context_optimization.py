from datetime import UTC, datetime, timedelta
from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models import Memory
from app.semantic.semantic_service import generate_embedding
from app.context.context_engine import ContextEngine
from app.graph.repository import reset_shared_graph
from app.pipeline.memory_pipeline import MemoryPipeline
from app.service import contradict_existing_memory, merge_existing_memories


def clear_db():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM memory_relationships;"))
        conn.execute(text("DELETE FROM memories;"))
        conn.commit()
    reset_shared_graph()


# ==========================================
# ACCEPTANCE TESTS A - L
# ==========================================

def test_a_direct_fact_beats_unrelated_memory():
    """Test A: Generic fact attribute match beats unrelated memories without domain hardcoding."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(
            content="I live in Bangalore.",
            category="profile",
            embedding=generate_embedding("I live in Bangalore."),
            state="active",
            importance=0.8,
        )
        m2 = Memory(
            content="I prefer tea.",
            category="preference",
            embedding=generate_embedding("I prefer tea."),
            state="active",
            importance=0.8,
        )
        m3 = Memory(
            content="I enjoy hiking.",
            category="habit",
            embedding=generate_embedding("I enjoy hiking."),
            state="active",
            importance=0.8,
        )
        db.add_all([m1, m2, m3])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What residence location do I live in?")

        assert len(ctx.profile) > 0
        assert "Bangalore" in ctx.profile[0]
    finally:
        db.close()


def test_b_entity_relevance():
    """Test B: Entity relevance bonus ranks matching entity memories above unrelated memories."""
    clear_db()
    db = SessionLocal()
    try:
        m_pref = Memory(
            content="I love drinking green tea.",
            category="preference",
            embedding=generate_embedding("I love drinking green tea."),
            state="active",
            importance=0.9,
        )
        m_event = Memory(
            content="I bought a blue jacket yesterday.",
            category="event",
            embedding=generate_embedding("I bought a blue jacket yesterday."),
            state="active",
            importance=0.4,
        )
        db.add_all([m_pref, m_event])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What do I prefer to drink?")

        assert len(ctx.preferences) > 0
        assert "green tea" in ctx.preferences[0]
    finally:
        db.close()


def test_c_update_current_fact_selection():
    """Test C: Fact update transition via MemoryPipeline produces single updated active memory."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Mumbai.", "profile")
        initial_id = res1["memory"].id

        # Pipeline UPDATE workflow
        res2 = pipeline.process("I live in Pune.", "profile")

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Where do I live?")

        assert len(ctx.profile) > 0
        assert "I live in Pune." in ctx.profile[0]
        assert "Mumbai" not in ctx.profile
    finally:
        db.close()


def test_d_historical_pipeline_contradiction_query():
    """Test D & Section 11: Real contradiction lineage historical query test."""
    clear_db()
    db = SessionLocal()
    try:
        m_new = Memory(
            content="I live in Pune.",
            category="profile",
            embedding=generate_embedding("I live in Pune."),
            state="active",
            is_contradicted=False,
            created_at=datetime.now(UTC),
        )
        db.add(m_new)
        db.commit()
        db.refresh(m_new)

        m_old = Memory(
            content="I live in Mumbai.",
            category="profile",
            embedding=generate_embedding("I live in Mumbai."),
            state="archived",
            is_contradicted=True,
            contradicted_by_id=m_new.id,
            created_at=datetime.now(UTC) - timedelta(days=30),
        )
        db.add(m_old)
        db.commit()

        context_engine = ContextEngine()

        # Current query prefers Pune
        ctx_curr = context_engine.build_context(db=db, query="Where do I live?")
        assert "I live in Pune." in ctx_curr.profile
        assert "I live in Mumbai." not in ctx_curr.profile

        # Historical query allows Mumbai
        ctx_hist = context_engine.build_context(db=db, query="Where did I live before?")
        all_hist = " ".join(ctx_hist.profile)
        assert "Mumbai" in all_hist
    finally:
        db.close()


def test_e_contradiction_filtering():
    """Test E: Contradicted memory is excluded from primary current context."""
    clear_db()
    db = SessionLocal()
    try:
        m_curr = Memory(
            content="I work at Apple.",
            category="profile",
            embedding=generate_embedding("I work at Apple."),
            state="active",
            is_contradicted=False,
        )
        db.add(m_curr)
        db.commit()
        db.refresh(m_curr)

        m_old = Memory(
            content="I work at Google.",
            category="profile",
            embedding=generate_embedding("I work at Google."),
            state="archived",
            is_contradicted=True,
            contradicted_by_id=m_curr.id,
        )
        db.add(m_old)
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Where do I work?")

        assert "I work at Apple." in ctx.profile
        assert "I work at Google." not in ctx.profile
    finally:
        db.close()


def test_f_merge_safety():
    """Test F: Merged archived memories (is_contradicted=False) are not treated as contradictions, preferring canonical."""
    clear_db()
    db = SessionLocal()
    try:
        canonical = Memory(
            content="I enjoy dark roast coffee.",
            category="preference",
            embedding=generate_embedding("I enjoy dark roast coffee."),
            state="active",
            importance=0.85,
            confidence=1.0,
        )
        merged_dup = Memory(
            content="I enjoy dark roast coffee.",
            category="preference",
            embedding=generate_embedding("I enjoy dark roast coffee."),
            state="archived",
            is_contradicted=False,
            contradicted_by_id=None,
            importance=0.8,
            confidence=0.9,
        )
        db.add_all([canonical, merged_dup])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What coffee do I enjoy?")

        assert len(ctx.preferences) > 0
        assert "I enjoy dark roast coffee." in ctx.preferences[0]
    finally:
        db.close()


def test_g_near_duplicate_diversity():
    """Test G: Near-duplicate claims are deduplicated via Jaccard overlap without adding context slots."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(
            content="I love espresso.",
            category="preference",
            embedding=generate_embedding("I love espresso."),
            state="active",
        )
        m2 = Memory(
            content="I really enjoy drinking espresso.",
            category="preference",
            embedding=generate_embedding("I really enjoy drinking espresso."),
            state="active",
        )
        m3 = Memory(
            content="Espresso is my favorite coffee.",
            category="preference",
            embedding=generate_embedding("Espresso is my favorite coffee."),
            state="active",
        )
        db.add_all([m1, m2, m3])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What is my favorite espresso?")

        assert len(ctx.preferences) < 3
    finally:
        db.close()


def test_j_real_token_budget_exceeded():
    """Test J & Section 9: Real multi-memory token budget test exceeding 1200 characters."""
    clear_db()
    db = SessionLocal()
    try:
        # Create 15 memories with ~100 chars each (total 1500 chars > 1200 max)
        memories = []
        for i in range(15):
            mem = Memory(
                content=f"Memory statement number {i:02d}: I enjoy eating fresh organic fruits and vegetables daily for health.",
                category="habit",
                embedding=generate_embedding(f"Memory statement number {i:02d}"),
                state="active",
                importance=0.9 - (i * 0.05),
            )
            memories.append(mem)

        db.add_all(memories)
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What are my daily habits?")

        total_chars = sum(len(m) for m in ctx.habits)
        assert total_chars <= 1200
        assert len(ctx.habits) > 0
        assert len(ctx.habits) < 15  # Weaker candidates were truncated safely
    finally:
        db.close()


# ==========================================
# NEGATIVE REGRESSION TESTS (Section 10)
# ==========================================

def test_negative_a_does_not_blindly_select_candidate_zero():
    """Negative A: Does not blindly select candidates[0] if lower candidate has better evidence score."""
    clear_db()
    db = SessionLocal()
    try:
        m_weak_cand0 = Memory(
            content="I visited a coffee shop last week.",
            category="event",
            embedding=generate_embedding("I visited a coffee shop last week."),
            state="active",
            importance=0.3,
        )
        m_strong_fact = Memory(
            content="I live in San Francisco.",
            category="profile",
            embedding=generate_embedding("I live in San Francisco."),
            state="active",
            importance=0.95,
        )
        db.add_all([m_weak_cand0, m_strong_fact])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What residence location do I live in?")

        assert "San Francisco" in ctx.profile[0]
    finally:
        db.close()


def test_negative_b_c_d_category_importance_recency_alone_insufficient():
    """Negative B, C, D: Category, importance, or recency alone does not determine correctness for fact query."""
    clear_db()
    db = SessionLocal()
    try:
        m_high_imp_irrel = Memory(
            content="My profile age is 30.",
            category="profile",
            embedding=generate_embedding("My profile age is 30."),
            state="active",
            importance=0.99,
        )
        m_fact_rel = Memory(
            content="I live in San Jose.",
            category="profile",
            embedding=generate_embedding("I live in San Jose."),
            state="active",
            importance=0.8,
        )
        db.add_all([m_high_imp_irrel, m_fact_rel])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Where do I live?")

        assert "San Jose" in ctx.profile[0]
    finally:
        db.close()


def test_negative_e_merged_archived_memories_not_treated_as_contradictions():
    """Negative E: Merged archived memories are not marked as is_contradicted=True."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(content="I drink green tea.", category="preference")
        m2 = Memory(content="I drink green tea.", category="preference")
        db.add_all([m1, m2])
        db.commit()

        # Merge memories via service helper
        canonical = merge_existing_memories(db, [m1, m2], "I drink green tea.", "preference")

        assert canonical.state == "active"
        assert canonical.is_contradicted is False
        assert m2.state == "archived"
        assert m2.is_contradicted is False  # Merged archived memories are NOT contradicted
    finally:
        db.close()


def test_negative_f_g_no_exact_or_near_duplicates():
    """Negative F & G: Does not return exact or near duplicates in context."""
    clear_db()
    db = SessionLocal()
    try:
        m1 = Memory(content="I play tennis.", category="habit", embedding=generate_embedding("I play tennis."), state="active")
        m2 = Memory(content="I play tennis.", category="habit", embedding=generate_embedding("I play tennis."), state="active")
        db.add_all([m1, m2])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What sports do I play?")

        assert len(ctx.habits) == 1
    finally:
        db.close()


def test_negative_h_contradicted_memories_not_primary_current_evidence():
    """Negative H: Does not select contradicted memories as primary current evidence."""
    clear_db()
    db = SessionLocal()
    try:
        m_new = Memory(content="I am vegetarian.", category="habit", state="active", is_contradicted=False)
        db.add(m_new)
        db.commit()
        db.refresh(m_new)

        m_old = Memory(content="I eat meat.", category="habit", state="archived", is_contradicted=True, contradicted_by_id=m_new.id)
        db.add(m_old)
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="What are my current eating habits?")

        assert "I am vegetarian." in ctx.habits
        assert "I eat meat." not in ctx.habits
    finally:
        db.close()


def test_negative_i_unrelated_profile_memories_not_included_solely_by_category():
    """Negative I: Unrelated profile memory not selected merely because it shares profile category."""
    clear_db()
    db = SessionLocal()
    try:
        m_work = Memory(content="I work at Microsoft.", category="profile", embedding=generate_embedding("I work at Microsoft."), state="active")
        m_hobby = Memory(content="My profile notes say I play guitar.", category="profile", embedding=generate_embedding("My profile notes say I play guitar."), state="active")
        db.add_all([m_work, m_hobby])
        db.commit()

        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Where do I work?")

        assert len(ctx.profile) > 0
        assert "Microsoft" in ctx.profile[0]
    finally:
        db.close()


def test_negative_j_empty_candidates_handled_gracefully():
    """Negative J: Context engine handles empty candidates gracefully without throwing."""
    clear_db()
    db = SessionLocal()
    try:
        context_engine = ContextEngine()
        ctx = context_engine.build_context(db=db, query="Unknown query")

        assert ctx is not None
        assert ctx.query == "Unknown query"
    finally:
        db.close()
