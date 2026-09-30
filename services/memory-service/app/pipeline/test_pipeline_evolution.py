"""
Memory pipeline control flow: one explicit path per decision, exact targets,
deterministic contradiction handling, and atomic evolution.
"""

import pytest

import app.pipeline.memory_pipeline as pipeline_module
from app.database import SessionLocal
from app.knowledge.knowledge_types import KnowledgeDecision
from app.knowledge.result_models import KnowledgeResult
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.testing_support import reset_database


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def by_content(db, content):
    db.expire_all()
    return db.query(Memory).filter(Memory.content == content).all()


def test_every_knowledge_decision_has_exactly_one_handler(db):
    pipeline = MemoryPipeline(db)
    assert set(pipeline._handlers) == set(KnowledgeDecision)


def test_contradiction_with_resolved_target(db):
    pipeline = MemoryPipeline(db)
    old = pipeline.process("I live in Mumbai.", "profile")["memory"]
    result = pipeline.process("I live in Pune.", "profile")

    assert result["knowledge"].decision == KnowledgeDecision.CONTRADICTION
    assert result["knowledge"].target_memory_id == old.id
    assert "conflicting_current_claims" in result["reason_codes"]

    new = result["memory"]
    (old_row,) = by_content(db, "I live in Mumbai.")
    assert new.state == "active" and not new.is_contradicted
    assert old_row.state == "archived"
    assert old_row.is_contradicted is True
    assert old_row.contradicted_by_id == new.id
    assert old_row.contradicted_by_id != old_row.id


def test_contradiction_target_recovered_by_wide_search(db, monkeypatch):
    """If classification reports CONTRADICTION without a target, the pipeline
    resolves the conflicting memory itself instead of losing the contradiction."""
    pipeline = MemoryPipeline(db)
    pipeline.process("I live in Mumbai.", "profile")

    def contradiction_without_target(parsed, candidates, historical=frozenset()):
        return KnowledgeResult(fact=None, decision=KnowledgeDecision.CONTRADICTION)

    monkeypatch.setattr(pipeline_module, "process_knowledge", contradiction_without_target)
    result = pipeline.process("I live in Pune.", "profile")

    assert "contradiction_target_resolved_by_wide_search" in result["reason_codes"]
    (old_row,) = by_content(db, "I live in Mumbai.")
    assert old_row.is_contradicted and old_row.state == "archived"
    assert old_row.contradicted_by_id == result["memory"].id


def test_unresolvable_contradiction_keeps_claim_and_archives_nothing(db, monkeypatch):
    pipeline = MemoryPipeline(db)
    pipeline.process("I like coffee.", "preference")

    def contradiction_without_target(parsed, candidates, historical=frozenset()):
        return KnowledgeResult(fact=None, decision=KnowledgeDecision.CONTRADICTION)

    monkeypatch.setattr(pipeline_module, "process_knowledge", contradiction_without_target)
    result = pipeline.process("I live in Pune.", "profile")

    assert "contradiction_target_unresolved" in result["reason_codes"]
    assert result["memory"].state == "active"
    db.expire_all()
    assert db.query(Memory).filter(Memory.state == "archived").count() == 0


def test_contradiction_only_archives_the_conflicting_candidate(db):
    pipeline = MemoryPipeline(db)
    for statement, category in [
        ("I live in Mumbai.", "profile"),
        ("I like coffee.", "preference"),
        ("I work at Google.", "profile"),
        ("My brother lives in Delhi.", "profile"),
    ]:
        pipeline.process(statement, category)

    pipeline.process("I live in Pune.", "profile")
    db.expire_all()
    archived = {m.content for m in db.query(Memory).filter(Memory.state == "archived")}
    assert archived == {"I live in Mumbai."}


def test_reasserted_contradicted_fact_is_reactivated(db):
    pipeline = MemoryPipeline(db)
    pipeline.process("I live in Mumbai.", "profile")
    pipeline.process("I live in Pune.", "profile")
    result = pipeline.process("I live in Mumbai.", "profile")

    (mumbai,) = by_content(db, "I live in Mumbai.")
    (pune,) = by_content(db, "I live in Pune.")
    assert result["memory"].id == mumbai.id
    assert mumbai.state != "archived" and not mumbai.is_contradicted
    assert pune.is_contradicted and pune.contradicted_by_id == mumbai.id


def test_evolution_is_atomic(db, monkeypatch):
    """A failure half-way through a contradiction leaves no partial state."""
    pipeline = MemoryPipeline(db)
    pipeline.process("I live in Mumbai.", "profile")

    def failing_contradict(*args, **kwargs):
        raise RuntimeError("simulated failure after the new memory was written")

    monkeypatch.setattr(pipeline_module, "contradict_existing_memory", failing_contradict)
    with pytest.raises(RuntimeError, match="simulated failure"):
        pipeline.process("I live in Pune.", "profile")

    assert by_content(db, "I live in Pune.") == []
    (mumbai,) = by_content(db, "I live in Mumbai.")
    assert mumbai.state == "active" and not mumbai.is_contradicted


def test_supersession_is_atomic(db, monkeypatch):
    pipeline = MemoryPipeline(db)
    pipeline.process("I live in Mumbai.", "profile")

    def failing_supersede(*args, **kwargs):
        raise RuntimeError("simulated lineage failure")

    monkeypatch.setattr(pipeline_module, "supersede_existing_fact_memory", failing_supersede)
    with pytest.raises(RuntimeError, match="simulated lineage failure"):
        pipeline.process("I moved to Pune.", "profile")

    assert by_content(db, "I moved to Pune.") == []


def test_supersession_reports_reason_codes(db):
    pipeline = MemoryPipeline(db)
    old = pipeline.process("I live in Mumbai.", "profile")["memory"]
    result = pipeline.process("I moved to Pune.", "profile")
    assert result["knowledge"].decision == KnowledgeDecision.SUPERSESSION
    assert result["knowledge"].target_memory_id == old.id
    assert {"same_entity", "same_attribute", "transition_detected"} <= set(result["reason_codes"])
