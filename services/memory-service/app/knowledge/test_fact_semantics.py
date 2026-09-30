from app.testing_support import reset_database
"""
Fact semantics regressions: value selection, attribute cardinality, planned
(FUTURE) facts and multi-message evolution safety.
"""

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.graph.repository import reset_shared_graph
from app.pipeline.memory_pipeline import MemoryPipeline
from app.understanding.memory_parser import parse_memory
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.attribute_schema import fact_domain_key, is_single_valued
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision


def clear_db():
    reset_database()


def fact_of(text_: str):
    return extract_fact(parse_memory(text_))


# ---------- extraction ----------

def test_direct_object_preferred_over_prepositional_adjunct():
    assert fact_of("I use my MacBook Air for development.").value == "MacBook Air"
    assert fact_of("I like coffee in the morning.").value == "coffee"


def test_work_maps_to_employer_only_for_employment_prepositions():
    assert fact_of("I work at Google.").attribute == "employer"
    assert fact_of("I work for Siemens.").attribute == "employer"
    assert fact_of("I primarily work on my MacBook Air.").attribute == "work_on"
    assert fact_of("I work with William.").attribute == "work_with"


def test_intention_verb_produces_future_fact_of_complement():
    fact = fact_of("I am planning to move to Bangalore.")
    assert (fact.entity, fact.attribute, fact.value) == ("user", "residence", "Bangalore")
    assert fact.temporal_state == "FUTURE"


# ---------- cardinality ----------

def test_attribute_cardinality():
    assert is_single_valued(fact_of("I live in Pune."))
    assert is_single_valued(fact_of("I work at Google."))
    assert not is_single_valued(fact_of("I like coffee."))
    assert not is_single_valued(fact_of("I use a MacBook Air."))


def test_multi_valued_domain_key_keeps_values_apart():
    assert fact_domain_key(fact_of("I like coffee.")) != fact_domain_key(fact_of("I like tea."))
    assert fact_domain_key(fact_of("I live in Pune.")) == fact_domain_key(fact_of("I live in Mumbai."))


def test_different_preferences_are_not_contradictions():
    assert detect_contradiction(parse_memory("I like tea."), "I like coffee.") is False
    assert detect_contradiction(parse_memory("I live in Pune."), "I live in Mumbai.") is True


def test_current_claim_does_not_contradict_future_plan():
    assert detect_contradiction(parse_memory("I live in Pune."), "I will move to Bangalore.") is False


# ---------- multi-message evolution ----------

def test_second_preference_does_not_archive_first():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I like coffee.", "preference")
        res = pipeline.process("I like tea.", "preference")
        assert res["knowledge"].decision != KnowledgeDecision.CONTRADICTION
        db.expire_all()
        coffee = db.query(Memory).filter(Memory.content == "I like coffee.").one()
        assert coffee.state != "archived"
        assert coffee.is_contradicted is False
    finally:
        db.close()


def test_device_reinforcement_does_not_create_false_contradiction():
    """Regression: 'I use my MacBook Air for development.' used to extract
    value='development' and archive 'I use a MacBook Air.' as a contradiction."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I use a MacBook Air.", "fact")
        pipeline.process("I primarily work on my MacBook Air.", "fact")
        pipeline.process("I use my MacBook Air for development.", "fact")
        db.expire_all()
        assert db.query(Memory).filter(Memory.is_contradicted.is_(True)).count() == 0
        live = db.query(Memory).filter(Memory.state != "archived").all()
        device_facts = [
            m for m in live
            if (fact_of(m.content).attribute, fact_of(m.content).value) == ("device", "MacBook Air")
        ]
        # One canonical device fact (merged/reinforced), not two competing ones.
        assert len(device_facts) == 1
    finally:
        db.close()


def test_planned_move_is_preserved_alongside_current_residence():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I moved to Pune.", "profile")
        pipeline.process("I am planning to move to Bangalore.", "profile")
        db.expire_all()

        plan = db.query(Memory).filter(Memory.content == "I am planning to move to Bangalore.").one()
        pune = db.query(Memory).filter(Memory.content == "I moved to Pune.").one()
        assert plan.state == "active" and not plan.is_contradicted
        assert pune.state == "active" and not pune.is_contradicted
        superseded_sources = {
            r.source_memory_id
            for r in db.query(MemoryRelationship).filter(
                MemoryRelationship.relationship_type == "superseded_by"
            )
        }
        assert pune.id not in superseded_sources
        assert plan.id not in superseded_sources
    finally:
        db.close()


def test_transition_never_supersedes_a_future_plan():
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        pipeline.process("I live in Mumbai.", "profile")
        pipeline.process("I will move to Bangalore.", "profile")
        pipeline.process("I moved to Pune.", "profile")
        db.expire_all()

        plan = db.query(Memory).filter(Memory.content == "I will move to Bangalore.").one()
        mumbai = db.query(Memory).filter(Memory.content == "I live in Mumbai.").one()
        rels = db.query(MemoryRelationship).filter(
            MemoryRelationship.relationship_type == "superseded_by"
        ).all()
        assert plan.id not in {r.source_memory_id for r in rels}
        assert mumbai.id in {r.source_memory_id for r in rels}
    finally:
        db.close()


def test_used_to_aspect_is_not_tool_usage():
    """Regression: 'I used to live in Mumbai.' was extracted as attribute 'tool'."""
    fact = fact_of("I used to live in Mumbai.")
    assert (fact.attribute, fact.value, fact.temporal_state) == ("residence", "Mumbai", "HISTORICAL")
    assert fact_of("I used Python to build it.").attribute == "tool"
