"""
PUT /memory/{id}: an explicit administrative correction with locking,
optimistic versioning, embedding refresh, graph rebuild and provenance.
It never bypasses these guarantees and never silently re-runs evolution.
"""

import threading

import pytest
from fastapi.testclient import TestClient

import app.graph.graph_service as graph_service_module
from app import lineage
from app.database import SessionLocal
from app.graph.sql_repository import SqlGraphRepository
from app.main import app
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.pipeline.memory_pipeline import MemoryPipeline
from app.provenance.models import MemoryEvidence
from app.semantic.semantic_service import generate_embedding
from app.testing_support import reset_database

client = TestClient(app)


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def edges(db):
    return {(e.source, e.relationship, e.target) for e in SqlGraphRepository(db).load().edges}


def node_ids(db):
    return {n.id for n in SqlGraphRepository(db).load().nodes}


def evidence(db, memory_id):
    db.expire_all()
    return db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == memory_id).order_by(MemoryEvidence.id).all()


def test_put_updates_text_embedding_version_graph_and_provenance(db):
    memory = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    before_version = memory.version

    response = client.put(f"/memory/{memory.id}", json={"content": "I work at BMW."})
    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "I work at BMW."
    assert body["version"] == before_version + 1
    assert body["state"] == "active"

    db.expire_all()
    stored = db.get(Memory, memory.id)
    assert list(stored.embedding) == pytest.approx(generate_embedding("I work at BMW."), abs=1e-6)

    # graph rebuilt from the new text; the stale edge and orphan entity are gone
    assert ("user", "works_at", "bmw") in edges(db)
    assert ("user", "lives_in", "mumbai") not in edges(db)
    assert "mumbai" not in node_ids(db)

    # provenance: original statement, then the admin edit with the previous text
    rows = evidence(db, memory.id)
    assert [r.decision for r in rows] == ["new", "admin_update"]
    assert rows[0].raw_text == "I live in Mumbai."
    assert (rows[1].raw_text, rows[1].previous_text, rows[1].source_type) == (
        "I work at BMW.", "I live in Mumbai.", "admin",
    )


def test_put_preserves_lifecycle_state_and_lineage(db):
    pipeline = MemoryPipeline(db)
    old = pipeline.process("I live in Mumbai.", "profile")["memory"]
    new = pipeline.process("I moved to Pune.", "profile")["memory"]
    contradicted = pipeline.process("I like coffee.", "preference")["memory"]
    contradicted.state, contradicted.is_contradicted = "archived", True
    db.commit()

    client.put(f"/memory/{old.id}", json={"content": "I lived in Mumbai for years."})
    client.put(f"/memory/{contradicted.id}", json={"content": "I like strong coffee."})

    db.expire_all()
    rels = {(r.source_memory_id, r.target_memory_id, r.relationship_type) for r in db.query(MemoryRelationship)}
    assert (old.id, new.id, lineage.SUPERSEDED_BY) in rels  # lineage untouched
    assert db.get(Memory, old.id).state == "active"
    edited = db.get(Memory, contradicted.id)
    assert (edited.state, edited.is_contradicted) == ("archived", True)


def test_put_expected_version_mismatch_is_rejected_without_changes(db):
    memory = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    stale = memory.version
    assert client.put(f"/memory/{memory.id}", json={"content": "I live in Goa.", "expected_version": stale}).status_code == 200

    response = client.put(f"/memory/{memory.id}", json={"content": "I live in Agra.", "expected_version": stale})
    assert response.status_code == 409
    db.expire_all()
    assert db.get(Memory, memory.id).content == "I live in Goa."
    assert [r.decision for r in evidence(db, memory.id)] == ["new", "admin_update"]


def test_put_unknown_memory_is_404(db):
    assert client.put("/memory/999999", json={"content": "x"}).status_code == 404


def test_put_is_atomic(db, monkeypatch):
    memory = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    before_version = memory.version

    def failing_persist(self, parsed, memory_id):
        raise RuntimeError("simulated graph failure")

    monkeypatch.setattr(graph_service_module.GraphService, "persist_memory", failing_persist)
    with pytest.raises(RuntimeError):
        client.put(f"/memory/{memory.id}", json={"content": "I work at BMW."})

    db.expire_all()
    stored = db.get(Memory, memory.id)
    assert (stored.content, stored.version) == ("I live in Mumbai.", before_version)
    assert [r.decision for r in evidence(db, memory.id)] == ["new"]
    assert ("user", "lives_in", "mumbai") in edges(db)


def test_concurrent_puts_serialize_without_lost_updates(db):
    memory = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    before_version = memory.version
    barrier = threading.Barrier(2)
    statuses = []

    def put(text):
        barrier.wait()
        statuses.append(client.put(f"/memory/{memory.id}", json={"content": text}).status_code)

    threads = [threading.Thread(target=put, args=(t,)) for t in ("I live in Goa.", "I live in Agra.")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert statuses == [200, 200]

    db.expire_all()
    stored = db.get(Memory, memory.id)
    assert stored.version == before_version + 2
    rows = evidence(db, memory.id)
    first, second = rows[1], rows[2]
    # serialized: the second edit saw the first edit's result
    assert second.previous_text == first.raw_text
    assert stored.content == second.raw_text


def test_concurrent_puts_with_same_expected_version_one_wins(db):
    memory = MemoryPipeline(db).process("I live in Mumbai.", "profile")["memory"]
    before_version = memory.version
    barrier = threading.Barrier(2)
    statuses = []

    def put(text):
        barrier.wait()
        statuses.append(client.put(
            f"/memory/{memory.id}", json={"content": text, "expected_version": before_version},
        ).status_code)

    threads = [threading.Thread(target=put, args=(t,)) for t in ("I live in Goa.", "I live in Agra.")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert sorted(statuses) == [200, 409]
    db.expire_all()
    assert db.get(Memory, memory.id).version == before_version + 1


def test_put_racing_an_evolution_in_the_same_domain_stays_consistent(db):
    """PUT and the pipeline serialize on the fact domain: whichever order they
    run in, exactly one current residence remains and lineage stays valid."""
    for _ in range(3):
        reset_database()
        setup = SessionLocal()
        target = MemoryPipeline(setup).process("I live in Mumbai.", "profile")["memory"]
        setup.close()
        barrier = threading.Barrier(2)
        errors = []

        def put():
            barrier.wait()
            response = client.put(f"/memory/{target.id}", json={"content": "I live in Goa."})
            if response.status_code != 200:
                errors.append(response.status_code)

        def evolve():
            session = SessionLocal()
            try:
                barrier.wait()
                MemoryPipeline(session).process("I live in Pune.", "profile")
            except Exception as exc:
                errors.append(exc)
            finally:
                session.close()

        threads = [threading.Thread(target=put), threading.Thread(target=evolve)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)
        assert not errors, errors

        check = SessionLocal()
        try:
            memories = check.query(Memory).all()
            live = [m for m in memories if m.state != "archived"]
            assert len(live) == 1, [(m.content, m.state) for m in memories]
            for m in memories:
                assert m.contradicted_by_id != m.id
                if m.is_contradicted:
                    assert m.contradicted_by_id == live[0].id
        finally:
            check.close()
