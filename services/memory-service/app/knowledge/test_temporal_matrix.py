"""
Temporal regression matrix (multi-message, end to end through the pipeline and
the ContextEngine).
"""

from datetime import UTC, datetime, timedelta

import pytest

from app import lineage
from app.context.context_engine import ContextEngine
from app.database import SessionLocal
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.knowledge_types import KnowledgeDecision
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.pipeline.memory_pipeline import MemoryPipeline
from app.testing_support import reset_database
from app.understanding.memory_parser import parse_memory


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def ingest(db, *statements, category="profile"):
    pipeline = MemoryPipeline(db)
    return [pipeline.process(s, category) for s in statements]


def row(db, content):
    db.expire_all()
    return db.query(Memory).filter(Memory.content == content).one()


def links(db, kind):
    db.expire_all()
    content = {m.id: m.content for m in db.query(Memory)}
    return {
        (content[r.source_memory_id], content[r.target_memory_id])
        for r in db.query(MemoryRelationship).filter(MemoryRelationship.relationship_type == kind)
    }


def answer(db, query):
    return [(e.content, e.temporal_state) for e in ContextEngine().build_context(db, query).evidence]


def fact(text):
    return extract_fact(parse_memory(text))


def test_current_conflict_is_a_contradiction(db):
    _, second = ingest(db, "I live in Mumbai.", "I live in Pune.")
    assert second["knowledge"].decision == KnowledgeDecision.CONTRADICTION
    assert row(db, "I live in Mumbai.").is_contradicted
    assert answer(db, "Where do I live?")[0][0] == "I live in Pune."


def test_explicit_transition_from_a_to_b_is_supersession(db):
    assert fact("I moved from Mumbai to Pune.").value == "Pune"
    _, second = ingest(db, "I live in Mumbai.", "I moved from Mumbai to Pune.")
    assert second["knowledge"].decision == KnowledgeDecision.SUPERSESSION
    mumbai = row(db, "I live in Mumbai.")
    assert mumbai.state == "active" and not mumbai.is_contradicted
    assert links(db, lineage.SUPERSEDED_BY) == {("I live in Mumbai.", "I moved from Mumbai to Pune.")}
    assert ("I live in Mumbai.", "HISTORICAL") in answer(db, "Where did I live before?")


def test_used_to_is_historical(db):
    assert fact("I used to live in Mumbai.").temporal_state == "HISTORICAL"
    ingest(db, "I used to live in Mumbai.", "I live in Pune.")
    assert answer(db, "Where do I live?")[0][0] == "I live in Pune."
    assert "I used to live in Mumbai." in [c for c, _ in answer(db, "Where did I live before?")]


def test_plan_is_future_and_never_answers_current(db):
    assert fact("I plan to move to Bangalore.").temporal_state == "FUTURE"
    ingest(db, "I live in Pune.", "I plan to move to Bangalore.")
    plan = row(db, "I plan to move to Bangalore.")
    assert plan.state == "active" and not plan.is_contradicted
    assert [c for c, _ in answer(db, "Where do I live?")] == ["I live in Pune."]
    assert answer(db, "Where do I plan to move?")[0] == ("I plan to move to Bangalore.", "FUTURE")


def test_time_passing_never_makes_a_plan_current(db):
    ingest(db, "I live in Pune.", "I plan to move to Bangalore.")
    plan = row(db, "I plan to move to Bangalore.")
    plan.created_at = datetime.now(UTC) - timedelta(days=400)
    db.commit()
    assert [c for c, _ in answer(db, "Where do I live?")] == ["I live in Pune."]
    assert answer(db, "Where do I plan to move?")[0][1] == "FUTURE"


def test_future_completion_links_plan_and_never_merges_it(db):
    results = ingest(db, "I live in Pune.", "I planned to move to Bangalore.", "I moved to Bangalore.")
    assert results[1]["memory"].id != results[2]["memory"].id  # no merge of plan and completion
    assert f"fulfilled_plan:{results[1]['memory'].id}" in results[2]["reason_codes"]

    plan = row(db, "I planned to move to Bangalore.")
    assert plan.state == "active"  # the plan is preserved as history
    assert links(db, lineage.FULFILLED_BY) == {("I planned to move to Bangalore.", "I moved to Bangalore.")}
    assert links(db, lineage.SUPERSEDED_BY) == {("I live in Pune.", "I moved to Bangalore.")}

    assert answer(db, "Where do I live?")[0] == ("I moved to Bangalore.", "CURRENT")
    future = answer(db, "Where will I move?")
    assert ("I planned to move to Bangalore.", "FUTURE") not in future
    history = dict(answer(db, "Where did I live before?"))
    assert history["I planned to move to Bangalore."] == "HISTORICAL"
    assert history["I live in Pune."] == "HISTORICAL"


def test_future_completion_without_prior_residence(db):
    first, second = ingest(db, "I will move to Bangalore.", "I moved to Bangalore.")
    assert second["knowledge"].decision != KnowledgeDecision.MERGE
    assert first["memory"].id != second["memory"].id
    assert links(db, lineage.FULFILLED_BY) == {("I will move to Bangalore.", "I moved to Bangalore.")}


def test_reassertion_cycle(db):
    ingest(db, "I live in Mumbai.", "I live in Pune.", "I live in Mumbai.")
    mumbai, pune = row(db, "I live in Mumbai."), row(db, "I live in Pune.")
    assert mumbai.state != "archived" and not mumbai.is_contradicted
    assert pune.is_contradicted and pune.contradicted_by_id == mumbai.id
    assert answer(db, "Where do I live?")[0][0] == "I live in Mumbai."


def test_multiple_values_coexist(db):
    ingest(db, "I like coffee.", "I like tea.", category="preference")
    assert {c for c, _ in answer(db, "What do I like?")} == {"I like coffee.", "I like tea."}
    assert db.query(Memory).filter(Memory.state == "archived").count() == 0


def test_entity_ambiguity_is_not_resolved_by_similarity(db):
    ingest(db, "Rahul Patel lives in Delhi.", "Rahul Sharma lives in Mumbai.", category="fact")
    # Different entities: no contradiction between their residences.
    assert db.query(Memory).filter(Memory.is_contradicted.is_(True)).count() == 0
    assert answer(db, "Where does Rahul Sharma live?")[0][0] == "Rahul Sharma lives in Mumbai."


@pytest.mark.parametrize("statement", [
    "I work with William.",          # 'will'
    "I visited Washington.",         # 'was'
    "I removed the old app.",        # 'moved'
])
def test_false_temporal_cues(statement):
    f = fact(statement)
    assert f.temporal_state != "FUTURE"
    if "removed" in statement:
        from app.knowledge.temporal_cues import has_transition_evidence
        assert not has_transition_evidence(statement)


def test_washington_is_not_a_past_cue_in_a_present_statement():
    assert fact("I live in Washington.").temporal_state == "CURRENT"


def test_merge_preserves_lineage_and_original_statements(db):
    first = ingest(db, "I use a MacBook Air.", category="fact")[0]["memory"]
    second = ingest(db, "I use my MacBook Air for development.", category="fact")[0]
    assert second["knowledge"].decision == KnowledgeDecision.MERGE
    assert second["memory"].id == first.id  # canonical record kept
    assert second["memory"].state == "active"


def test_merge_links_archived_duplicates_to_canonical(db):
    from app.service import merge_existing_memories

    a = Memory(content="I drink green tea.", category="preference", state="active")
    b = Memory(content="I drink green tea daily.", category="preference", state="active")
    db.add_all([a, b])
    db.commit()
    canonical = merge_existing_memories(db, [a, b], "I drink green tea.", "preference")
    assert canonical.id == a.id
    assert row(db, "I drink green tea daily.").state == "archived"
    assert links(db, lineage.MERGED_INTO) == {("I drink green tea daily.", "I drink green tea.")}
