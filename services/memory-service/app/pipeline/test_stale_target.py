"""
Stale classification: a decision reasoned on state that changed before it is
written must never be applied. Detected by per-domain serialization, row
locks and the optimistic memories.version check; resolved by a bounded
retry from fresh state.
"""

import threading
import time

import pytest

import app.pipeline.memory_pipeline as pipeline_module
from app.database import SessionLocal
from app.knowledge.knowledge_types import KnowledgeDecision
from app.models import Memory
from app.pipeline.memory_pipeline import MAX_ATTEMPTS, EvolutionConflict, MemoryPipeline
from app.reflection_service import ReflectionEngine
from app.service import archive_memory, bump_version, lock_memory, reinforce_existing_memory
from app.testing_support import reset_database


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def spy_classification(monkeypatch, after_first=None, after_every=None):
    """Run a concurrent writer right after classification (inside the evolution)."""
    original = pipeline_module.process_knowledge
    calls = {"n": 0}

    def spy(*args, **kwargs):
        result = original(*args, **kwargs)
        calls["n"] += 1
        if after_every is not None or (after_first is not None and calls["n"] == 1):
            (after_every or after_first)()
        return result

    monkeypatch.setattr(pipeline_module, "process_knowledge", spy)
    return calls


def concurrent_content_edit(memory_id, new_content):
    """A committed edit from another transaction (bumps the version)."""
    def edit():
        other = SessionLocal()
        try:
            m = lock_memory(other, other.get(Memory, memory_id))
            m.content = new_content
            bump_version(m)
            other.commit()
        finally:
            other.close()
    return edit


def test_stale_target_content_is_detected_and_reclassified(db, monkeypatch):
    """Regression (reproduced before the fix): the target was edited to
    'I like tea.' after classification, yet was archived as a contradicted
    residence."""
    target = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    calls = spy_classification(monkeypatch, after_first=concurrent_content_edit(target.id, "I like tea."))

    result = MemoryPipeline(db).process("I live in Pune.", "profile")

    assert calls["n"] == 2  # stale decision rejected, reclassified from fresh state
    assert result["knowledge"].decision != KnowledgeDecision.CONTRADICTION
    db.expire_all()
    edited = db.get(Memory, target.id)
    assert edited.content == "I like tea."
    assert edited.state == "active" and not edited.is_contradicted


def test_target_archived_after_classification_is_not_evolved(db, monkeypatch):
    target = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    calls = spy_classification(monkeypatch, after_first=lambda: archive_memory(target.id))

    result = MemoryPipeline(db).process("I live in Pune.", "profile")

    assert calls["n"] == 2
    db.expire_all()
    archived = db.get(Memory, target.id)
    assert archived.state == "archived"
    assert archived.is_contradicted is False
    assert archived.contradicted_by_id is None
    assert result["memory"].state == "active"


def test_retry_is_bounded_and_leaves_no_partial_state(db, monkeypatch):
    target = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    counter = {"i": 0}

    def edit_every_time():
        counter["i"] += 1
        concurrent_content_edit(target.id, f"I live in Mumbai. ({counter['i']})")()

    calls = spy_classification(monkeypatch, after_every=edit_every_time)
    with pytest.raises(EvolutionConflict):
        MemoryPipeline(db).process("I live in Pune.", "profile")

    assert calls["n"] == MAX_ATTEMPTS
    db.expire_all()
    assert db.query(Memory).filter(Memory.content == "I live in Pune.").count() == 0
    assert db.get(Memory, target.id).state == "active"


def test_concurrent_conflicting_statements_never_both_stay_current():
    """Regression (reproduced before the fix in 2 of 5 trials): with no existing
    row to lock, two conflicting residences were both stored as NEW."""
    for _ in range(5):
        reset_database()
        barrier = threading.Barrier(2)
        errors = []

        def worker(statement):
            session = SessionLocal()
            try:
                pipeline = MemoryPipeline(session)
                barrier.wait()
                pipeline.process(statement, "profile")
            except Exception as exc:
                errors.append(exc)
            finally:
                session.close()

        threads = [threading.Thread(target=worker, args=(s,)) for s in ("I live in Pune.", "I live in Delhi.")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)
        assert not errors, errors

        session = SessionLocal()
        try:
            memories = session.query(Memory).all()
            live = [m for m in memories if m.state != "archived"]
            assert len(live) == 1, [(m.content, m.state) for m in memories]
            (loser,) = [m for m in memories if m.is_contradicted]
            assert loser.contradicted_by_id == live[0].id != loser.id
        finally:
            session.close()


def test_reflection_counters_do_not_lose_concurrent_reinforcement(db):
    """Deterministic lost-update check for reflection: its memory objects are
    loaded before a concurrent reinforcement commits."""
    memory = Memory(content="I live in Pune.", category="profile", state="active", access_count=0)
    db.add(memory)
    db.commit()
    memory_id = memory.id

    reflect_session = SessionLocal()
    used = [reflect_session.get(Memory, memory_id)]  # loaded with access_count = 0

    holder = SessionLocal()
    reinforce_existing_memory(holder, lock_memory(holder, holder.get(Memory, memory_id)), commit=False)

    errors = []

    def reflect():
        try:
            ReflectionEngine().reflect(reflect_session, "Where do I live?", "You live in Pune.", used)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=reflect)
    worker.start()
    time.sleep(1.0)  # reflection now waits on the row lock
    holder.commit()
    holder.close()
    worker.join(timeout=60)
    reflect_session.close()

    assert not errors, errors
    db.expire_all()
    assert db.get(Memory, memory_id).access_count == 2
