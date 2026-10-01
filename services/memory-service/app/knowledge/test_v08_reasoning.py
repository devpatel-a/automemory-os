from app.testing_support import reset_database
from app.database import SessionLocal
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.understanding.memory_parser import parse_memory
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.classifier import classify_knowledge, is_merge_equivalent
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.decision.decision_types import MemoryAction
from app.pipeline.memory_pipeline import MemoryPipeline
from app.graph.graph_service import GraphService
from app.context.context_engine import ContextEngine


def clear_db():
    reset_database()


def get_memory_temporal_state(db, memory: Memory) -> str:
    """Helper to determine effective temporal state of a stored memory including supersession lineage."""
    rel = (
        db.query(MemoryRelationship)
        .filter(
            MemoryRelationship.source_memory_id == memory.id,
            MemoryRelationship.relationship_type == "superseded_by",
        )
        .first()
    )
    if rel:
        return "HISTORICAL"
    fact = extract_fact(parse_memory(memory.content))
    return fact.temporal_state if fact else "CURRENT"


# ==========================================
# 1. TEMPORAL FACT STATE & NORMALIZATION
# ==========================================

def test_v08_current_fact():
    """Test 1: Current fact extraction ('I live in Pune.')."""
    parsed = parse_memory("I live in Pune.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.temporal_state == "CURRENT"
    assert fact.value == "Pune"


def test_v08_historical_fact():
    """Test 2: Historical fact extraction ('I used to live in Mumbai.')."""
    parsed = parse_memory("I used to live in Mumbai.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.temporal_state == "HISTORICAL"
    assert fact.value == "Mumbai"


def test_v08_future_fact():
    """Test 3: Future fact extraction ('I will move to Bangalore.')."""
    parsed = parse_memory("I will move to Bangalore.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.temporal_state == "FUTURE"
    assert fact.value == "Bangalore"


# ==========================================
# 2. SUPERSESSION & HISTORICAL PRESERVATION (CRITICAL FIX 1 & 3)
# ==========================================

def test_v08_current_to_historical_supersession():
    """Test 4: Current -> Historical Supersession ('I lived in Mumbai.' -> 'I live in Pune.')."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I lived in Mumbai.", "profile")
        m1_id = res1["memory"].id

        res2 = pipeline.process("I live in Pune.", "profile")
        m2_id = res2["memory"].id

        db.expire_all()
        mems = db.query(Memory).order_by(Memory.id).all()
        assert len(mems) == 2

        m1 = mems[0]
        m2 = mems[1]

        # Superseded historical fact MUST NOT have is_contradicted = True
        assert m1.is_contradicted is False
        assert m1.state == "active"
        assert m2.is_contradicted is False
        assert m2.state == "active"

        # Verify lineage established via MemoryRelationship table
        rel = (
            db.query(MemoryRelationship)
            .filter(
                MemoryRelationship.source_memory_id == m1_id,
                MemoryRelationship.target_memory_id == m2_id,
                MemoryRelationship.relationship_type == "superseded_by",
            )
            .first()
        )
        assert rel is not None
    finally:
        db.close()


def test_v08_multiple_transitions_preservation_strengthened():
    """Test 5 & Section 5: Mumbai -> Pune -> Bangalore strengthens actual semantic state assertions."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I lived in Mumbai.", "profile")
        res2 = pipeline.process("I moved to Pune.", "profile")
        res3 = pipeline.process("I moved to Bangalore.", "profile")

        db.expire_all()
        mems = db.query(Memory).order_by(Memory.id).all()
        assert len(mems) == 3

        m1, m2, m3 = mems[0], mems[1], mems[2]

        # Verify all 3 remain active and NOT contradicted
        assert m1.state != "archived" and m1.is_contradicted is False
        assert m2.state != "archived" and m2.is_contradicted is False
        assert m3.state != "archived" and m3.is_contradicted is False

        # Verify semantic temporal states (Mumbai=HISTORICAL, Pune=HISTORICAL, Bangalore=CURRENT)
        assert get_memory_temporal_state(db, m1) == "HISTORICAL"
        assert get_memory_temporal_state(db, m2) == "HISTORICAL"
        assert get_memory_temporal_state(db, m3) == "CURRENT"
    finally:
        db.close()


def test_v08_non_unique_value_transitions_identity():
    """Test 6 & Section 6: Non-unique value transitions (Mumbai -> Pune -> Mumbai) work via object identity."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I lived in Mumbai.", "profile")
        res2 = pipeline.process("I moved to Pune.", "profile")
        res3 = pipeline.process("I moved to Mumbai.", "profile")

        db.expire_all()
        mems = db.query(Memory).order_by(Memory.id).all()
        assert len(mems) == 3

        m1_id, m2_id, m3_id = mems[0].id, mems[1].id, mems[2].id

        # Verify three distinct memory IDs
        assert m1_id != m2_id
        assert m2_id != m3_id
        assert m1_id != m3_id

        # Verify contents preserved
        assert mems[0].content == "I lived in Mumbai."
        assert mems[1].content == "I moved to Pune."
        assert mems[2].content == "I moved to Mumbai."

        # Verify historical vs current semantics
        assert get_memory_temporal_state(db, mems[0]) == "HISTORICAL"
        assert get_memory_temporal_state(db, mems[1]) == "HISTORICAL"
        assert get_memory_temporal_state(db, mems[2]) == "CURRENT"
    finally:
        db.close()


# ==========================================
# 3. CURRENT VS FUTURE & TRANSITION vs CONTRADICTION
# ==========================================

def test_v08_future_preservation():
    """Test 7 & Section 7: CURRENT + FUTURE facts preserved without premature supersession ('I live in Pune.' + 'I will move to Bangalore.')."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Pune.", "profile")
        res2 = pipeline.process("I will move to Bangalore.", "profile")

        db.expire_all()
        mems = db.query(Memory).order_by(Memory.id).all()
        assert len(mems) == 2

        f1 = extract_fact(parse_memory(mems[0].content))
        f2 = extract_fact(parse_memory(mems[1].content))

        assert f1.temporal_state == "CURRENT"
        assert f2.temporal_state == "FUTURE"
        assert mems[0].is_contradicted is False
    finally:
        db.close()


def test_v08_explicit_transition():
    """Test 8 & Section 8: 'I live in Pune.' -> 'I moved to Bangalore.' produces SUPERSESSION."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Pune.", "profile")
        res2 = pipeline.process("I moved to Bangalore.", "profile")

        assert res2["decision"].action == MemoryAction.UPDATE
        assert res2["knowledge"].decision == KnowledgeDecision.SUPERSESSION

        db.expire_all()
        mems = db.query(Memory).order_by(Memory.id).all()
        assert len(mems) == 2

        # Pune is historical, Bangalore is current, Pune is NOT contradicted
        assert mems[0].is_contradicted is False
        assert mems[0].state == "active"
        assert mems[1].state == "active"
        assert get_memory_temporal_state(db, mems[0]) == "HISTORICAL"
        assert get_memory_temporal_state(db, mems[1]) == "CURRENT"
    finally:
        db.close()


def test_v08_contradiction_without_transition():
    """Test 9 & Section 9: 'I live in Mumbai.' -> 'I live in Pune.' produces CONTRADICTION."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Mumbai.", "profile")
        m1_id = res1["memory"].id

        res2 = pipeline.process("I live in Pune.", "profile")

        assert res2["knowledge"].decision == KnowledgeDecision.CONTRADICTION
        assert res2["decision"].action == MemoryAction.ARCHIVE

        db.expire_all()
        m1 = db.query(Memory).filter(Memory.id == m1_id).first()
        assert m1.is_contradicted is True
        assert m1.contradicted_by_id == res2["memory"].id
        assert m1.state == "archived"
    finally:
        db.close()


# ==========================================
# 4. NEGATION / "NO LONGER" SEMANTICS (INTEGRATION TEST)
# ==========================================

def test_v08_no_longer_negation_semantics():
    """Extractor test: 'I do not live in Mumbai anymore.' marks fact historical without dummy value."""
    parsed = parse_memory("I do not live in Mumbai anymore.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.is_negated is True
    assert fact.temporal_state == "HISTORICAL"
    assert fact.value == "Mumbai"
    assert fact.value != "unknown"


def test_v08_no_longer_pipeline_integration():
    """Pipeline integration test: 'I live in Mumbai.' then 'I do not live in Mumbai anymore.'"""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Mumbai.", "profile")
        m1_id = res1["memory"].id

        res2 = pipeline.process("I do not live in Mumbai anymore.", "profile")

        db.expire_all()
        m1 = db.query(Memory).filter(Memory.id == m1_id).first()
        assert m1 is not None
        assert m1.state == "active"
        assert m1.is_contradicted is False
        assert get_memory_temporal_state(db, m1) == "HISTORICAL"

        # Verify no dummy replacement location "unknown" was fabricated as a fake memory value
        all_mems = db.query(Memory).all()
        all_contents = [m.content.lower() for m in all_mems]
        assert not any("unknown" in c for c in all_contents)
    finally:
        db.close()


# ==========================================
# 5. TEMPORAL QUERY INTENT (CONTEXT ENGINE)
# ==========================================

def test_v08_context_engine_temporal_queries():
    """Test 13 & Micro Fix 3: ContextEngine temporal intent with 'I moved to Pune.'."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I lived in Mumbai.", "profile")
        pipeline.process("I moved to Pune.", "profile")

        engine_ctx = ContextEngine()

        # Current query prefers Pune
        pkg_curr = engine_ctx.build_context(db, "What city do I live in?")
        assert pkg_curr is not None
        curr_contents = pkg_curr.profile + pkg_curr.other
        assert any("Pune" in c for c in curr_contents)

        # Historical query prefers Mumbai
        pkg_hist = engine_ctx.build_context(db, "Where did I live before?")
        assert pkg_hist is not None
        hist_contents = pkg_hist.profile + pkg_hist.other
        assert any("Mumbai" in c for c in hist_contents)
    finally:
        db.close()


# ==========================================
# 6. EXPLICIT ENTITY RELATIONSHIPS & RELATIONSHIP DETECTOR SAFETY
# ==========================================

def test_v08_explicit_entity_relationship_safety():
    """Test 11 & Micro Fix 1: Explicit entity relationship vs non-user subject relationship safety."""
    f1 = extract_fact(parse_memory("My friend Rahul works at Google."))
    assert f1 is not None
    assert f1.entity == "Rahul"
    assert f1.relationship_to_user == "friend"
    assert f1.value == "Google"

    # Verify relationship_detector creates friend_of edge to user, but non-user subject edges use rahul as source
    parsed_rahul = parse_memory("Rahul works at Google.")
    service = GraphService()
    graph = service.process_memory(parsed_rahul, memory_id=1)

    # Verify user -> rahul -> works_with is NOT created when sentence says "Rahul works at Google."
    user_works = [e for e in graph.edges if e.source == "user" and e.relationship in ("works_with", "works_at")]
    assert len(user_works) == 0

    # Verify rahul -> google edge is created instead
    rahul_edges = [e for e in graph.edges if e.source == "rahul"]
    assert len(rahul_edges) > 0
    assert rahul_edges[0].target == "google"


def test_v08_conservative_entity_resolution():
    """Test 12: Conservative entity resolution prevents false merges ('Rahul Patel' vs 'Rahul Sharma')."""
    f1 = extract_fact(parse_memory("Rahul Patel works at Google."))
    f2 = extract_fact(parse_memory("Rahul Sharma works at Microsoft."))

    assert f1 is not None and f2 is not None
    assert f1.entity == "Rahul Patel"
    assert f2.entity == "Rahul Sharma"
    assert f1.entity != f2.entity
