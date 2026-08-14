from app.database import SessionLocal, engine
from sqlalchemy import text
from app.models import Memory
from app.understanding.memory_parser import parse_memory
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.classifier import classify_knowledge, is_merge_equivalent
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.decision.decision_types import MemoryAction
from app.pipeline.memory_pipeline import MemoryPipeline
from app.graph.repository import reset_shared_graph


def clear_db():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM memory_relationships;"))
        conn.execute(text("DELETE FROM memories;"))
        conn.commit()
    reset_shared_graph()


# ==========================================
# ACCEPTANCE TESTS A - M
# ==========================================

def test_a_preference():
    """Test A: Preference extraction ('I prefer espresso.')."""
    parsed = parse_memory("I prefer espresso.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "user"
    assert fact.attribute == "preference"
    assert fact.value == "espresso"
    assert fact.fact_type == "PREFERENCE"


def test_b_location():
    """Test B: Location extraction ('I live in Pune.')."""
    parsed = parse_memory("I live in Pune.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "user"
    assert fact.attribute in ("residence", "location")
    assert fact.value == "Pune"
    assert fact.fact_type == "LOCATION"


def test_c_employment():
    """Test C: Employment extraction ('I work at Google.')."""
    parsed = parse_memory("I work at Google.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "user"
    assert fact.attribute == "employer"
    assert fact.value == "Google"
    assert fact.fact_type == "EMPLOYMENT"


def test_d_learning():
    """Test D: Learning topic extraction ('I am learning FastAPI.')."""
    parsed = parse_memory("I am learning FastAPI.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "user"
    assert fact.attribute == "learning_topic"
    assert fact.value == "FastAPI"
    assert fact.fact_type == "LEARNING"


def test_e_multi_token_value():
    """Test E: Multi-token value preservation ('I live in New York.')."""
    parsed = parse_memory("I live in New York.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.value == "New York"
    assert fact.value != "New"


def test_f_paraphrase_normalization():
    """Test F: Paraphrase normalization across varied syntactic expressions."""
    f1 = extract_fact(parse_memory("I live in Pune."))
    f2 = extract_fact(parse_memory("I am living in Pune."))
    f3 = extract_fact(parse_memory("My current city is Pune."))

    assert f1 is not None and f2 is not None and f3 is not None
    assert f1.entity == f2.entity == f3.entity == "user"
    assert f1.attribute in ("residence", "location")
    assert f2.attribute in ("residence", "location")
    assert f3.attribute in ("residence", "location")
    assert f1.value.lower() == f2.value.lower() == f3.value.lower() == "pune"


def test_g_update():
    """Test G: SUPERSESSION for existing location Mumbai vs incoming transition to Pune."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Mumbai.", "profile")
        assert res1["decision"].action == MemoryAction.STORE

        parsed2 = parse_memory("I moved to Pune.")
        candidates = [(res1["memory"], 0.15)]

        decision = classify_knowledge(parsed2, candidates)
        assert decision == KnowledgeDecision.SUPERSESSION
    finally:
        db.close()


def test_h_reinforcement():
    """Test H: REINFORCEMENT for duplicate preference claims."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I prefer espresso.", "preference")

        parsed2 = parse_memory("I prefer espresso.")
        candidates = [(res1["memory"], 0.0)]

        decision = classify_knowledge(parsed2, candidates)
        assert decision in (KnowledgeDecision.REINFORCEMENT, KnowledgeDecision.MERGE)
    finally:
        db.close()


def test_i_unrelated_facts():
    """Test I: Unrelated facts (location Pune vs preference espresso) never UPDATE or MERGE."""
    clear_db()
    db = SessionLocal()
    try:
        m_loc = Memory(content="I live in Pune.", category="profile")
        parsed_pref = parse_memory("I prefer espresso.")
        candidates = [(m_loc, 0.40)]

        decision = classify_knowledge(parsed_pref, candidates)
        assert decision not in (KnowledgeDecision.UPDATE, KnowledgeDecision.MERGE)
    finally:
        db.close()


def test_j_contradiction():
    """Test J: Contradiction operates only on comparable facts."""
    parsed_pune = parse_memory("I live in Pune.")
    parsed_espresso = parse_memory("I prefer espresso.")

    assert detect_contradiction(parsed_pune, "I live in Mumbai.") is True
    assert detect_contradiction(parsed_espresso, "I live in Pune.") is False


def test_k_entity_separation():
    """Test K: Entity separation ('My company is Google.')."""
    parsed = parse_memory("My company is Google.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "user"
    assert fact.attribute in ("company", "employer")
    assert fact.value == "Google"


def test_l_unknown_ambiguous_input():
    """Test L: Ambiguous input ('I really like this.') does not fabricate hallucinated facts."""
    parsed = parse_memory("I really like this.")
    fact = extract_fact(parsed)
    if fact is not None:
        assert fact.confidence <= 0.40


def test_m_domain_generalization():
    """Test M: Extraction generalizes across coffee, city, company, programming, device, sport."""
    inputs = [
        ("I prefer espresso.", "espresso"),
        ("I live in Pune.", "Pune"),
        ("I work at Google.", "Google"),
        ("My favorite language is Python.", "Python"),
        ("I use a MacBook Air.", "MacBook Air"),
        ("I play tennis.", "tennis"),
    ]
    for text_in, expected_val in inputs:
        fact = extract_fact(parse_memory(text_in))
        assert fact is not None, f"Failed for input: {text_in}"
        assert expected_val.lower() in fact.value.lower(), f"Expected {expected_val} in {fact.value}"


# ==========================================
# NON-USER ENTITY EXTRACTION TESTS
# ==========================================

def test_other_entity_extraction_rahul():
    """Test non-user entity extraction: 'My friend Rahul works at Google.'"""
    parsed = parse_memory("My friend Rahul works at Google.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "Rahul"
    assert fact.attribute == "employer"
    assert fact.value == "Google"


def test_other_entity_extraction_brother():
    """Test non-user entity extraction: 'My brother lives in Pune.'"""
    parsed = parse_memory("My brother lives in Pune.")
    fact = extract_fact(parsed)
    assert fact is not None
    assert fact.entity == "brother"
    assert fact.attribute in ("residence", "location")
    assert fact.value == "Pune"


# ==========================================
# REQUIRED OBJECT-CONTEXT TESTS
# ==========================================

def test_object_context_macbook_device():
    """Object Context Test 1: 'I use a MacBook Air.' -> device."""
    fact = extract_fact(parse_memory("I use a MacBook Air."))
    assert fact is not None
    assert fact.attribute == "device"
    assert fact.fact_type == "DEVICE"
    assert "MacBook Air" in fact.value


def test_object_context_computer_device():
    """Object Context Test 2: 'I use a computer for work.' -> device."""
    fact = extract_fact(parse_memory("I use a computer for work."))
    assert fact is not None
    assert fact.attribute == "device"
    assert fact.fact_type == "DEVICE"


def test_object_context_workstation_device():
    """Object Context Test 3: 'I use a workstation.' -> device."""
    fact = extract_fact(parse_memory("I use a workstation."))
    assert fact is not None
    assert fact.attribute == "device"
    assert fact.fact_type == "DEVICE"
    assert "workstation" in fact.value


def test_object_context_python_for_work_not_device():
    """Object Context Test 4: 'I use Python for work.' -> NOT device."""
    fact = extract_fact(parse_memory("I use Python for work."))
    assert fact is not None
    assert fact.attribute != "device"
    assert fact.fact_type != "DEVICE"


def test_object_context_bare_python_not_device():
    """Object Context Test 5: 'I use Python.' -> must NOT automatically become device."""
    fact = extract_fact(parse_memory("I use Python."))
    assert fact is not None
    assert fact.attribute != "device"
    assert fact.fact_type != "DEVICE"


def test_object_context_programming_language_not_device():
    """Object Context Test 6: 'I use a programming language.' -> must NOT automatically become device."""
    fact = extract_fact(parse_memory("I use a programming language."))
    assert fact is not None
    assert fact.attribute != "device"
    assert fact.fact_type != "DEVICE"


# ==========================================
# TEMPORAL COMPOUND SENTENCE TEST
# ==========================================

def test_temporal_compound_sentence_single_fact_contract():
    """
    Temporal Test: 'I lived in Mumbai before moving to Pune.'
    Verifies documented limitation contract.
    """
    fact = extract_fact(parse_memory("I lived in Mumbai before moving to Pune."))
    assert fact is not None
    assert fact.temporal_info == "past"
    assert "Pune" in fact.value or "Mumbai" in fact.value


# ==========================================
# STRUCTURAL GENERALIZATION TESTS
# ==========================================

def test_structural_generalization_varied_domains():
    """Structural Generalization Test across varied domains without hardcoded value branches."""
    test_cases = [
        ("I prefer tea.", "user", "preference", "tea"),
        ("I live in Tokyo.", "user", "residence", "Tokyo"),
        ("I work at Microsoft.", "user", "employer", "Microsoft"),
        ("I am learning Rust.", "user", "learning_topic", "Rust"),
        ("I use an iPhone.", "user", "device", "iPhone"),
        ("I play cricket.", "user", "activity", "cricket"),
    ]
    for text_in, expected_ent, expected_attr, expected_val in test_cases:
        fact = extract_fact(parse_memory(text_in))
        assert fact is not None, f"Failed for: {text_in}"
        assert fact.entity == expected_ent
        assert fact.attribute == expected_attr
        assert expected_val.lower() in fact.value.lower()


# ==========================================
# NEGATIVE STRUCTURAL TESTS
# ==========================================

def test_negative_structural_python_not_device():
    """Negative Structural Test 1: Verifies 'I use Python for work' is not assigned device."""
    fact = extract_fact(parse_memory("I use Python for work."))
    assert fact is not None
    assert fact.attribute != "device"
    assert fact.fact_type != "DEVICE"


def test_negative_structural_non_user_entity_rahul():
    """Negative Structural Test 2: Verifies 'My friend Rahul works at Google' is not assigned entity=user."""
    fact = extract_fact(parse_memory("My friend Rahul works at Google."))
    assert fact is not None
    assert fact.entity != "user"
    assert fact.entity == "Rahul"


def test_negative_structural_non_user_entity_brother():
    """Negative Structural Test 3: Verifies 'My brother lives in Pune' is not assigned entity=user."""
    fact = extract_fact(parse_memory("My brother lives in Pune."))
    assert fact is not None
    assert fact.entity != "user"
    assert fact.entity == "brother"


# ==========================================
# CONFIDENCE TESTS
# ==========================================

def test_confidence_deterministic_monotonicity():
    """Confidence Test: High confidence for complete facts, lower for ambiguous."""
    fact_clear = extract_fact(parse_memory("I live in New York."))
    fact_ambig = extract_fact(parse_memory("I really like this."))

    assert fact_clear is not None
    if fact_ambig is not None:
        assert fact_clear.confidence > fact_ambig.confidence


# ==========================================
# MEMORY PIPELINE INTEGRATION TEST
# ==========================================

def test_memory_pipeline_end_to_end_integration():
    """Integration Test: Raw input -> Pipeline -> Understanding -> Knowledge -> Decision -> Evolution."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I work at Google.", "profile")
        assert res1["decision"].action == MemoryAction.STORE
        assert res1["memory"].content == "I work at Google."

        res2 = pipeline.process("I transferred to Apple.", "profile")
        assert res2["decision"].action == MemoryAction.UPDATE
        assert res2["memory"].content == "I transferred to Apple."
    finally:
        db.close()
