"""
DELETE /memory/{id}: archival by default (non-destructive lifecycle change);
permanent purge only with purge=true, with auditable lineage effects, graph
cleanup and no dangling references.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import lineage
from app.database import SessionLocal
from app.graph.sql_repository import SqlGraphRepository
from app.main import app
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.pipeline.memory_pipeline import MemoryPipeline
from app.provenance.models import MemoryEvidence
from app.retrieval_service import retrieve_memories
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


def ingest(db, *statements):
    pipeline = MemoryPipeline(db)
    return [pipeline.process(s, "profile")["memory"] for s in statements]


def count(db, sql, **params):
    return db.execute(text(sql), params).scalar()


def decisions(db, memory_id):
    db.expire_all()
    return [e.decision for e in db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == memory_id).order_by(MemoryEvidence.id)]


def assert_no_dangling_references(db):
    """FK integrity: nothing references a memory or entity that no longer exists."""
    checks = {
        "evidence": "SELECT count(*) FROM memory_evidence e WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = e.memory_id)",
        "lineage": "SELECT count(*) FROM memory_relationships r WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = r.source_memory_id) OR NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = r.target_memory_id)",
        "memory_entities": "SELECT count(*) FROM memory_entities me WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = me.memory_id)",
        "entity_relationships": "SELECT count(*) FROM entity_relationships er WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = er.memory_id)",
        "contradicted_by": "SELECT count(*) FROM memories x WHERE x.contradicted_by_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = x.contradicted_by_id)",
        "orphan_entities": "SELECT count(*) FROM entities e WHERE NOT EXISTS (SELECT 1 FROM memory_entities me WHERE me.entity_id = e.id) AND NOT EXISTS (SELECT 1 FROM entity_aliases a WHERE a.entity_id = e.id)",
    }
    assert {k: count(db, q) for k, q in checks.items()} == {k: 0 for k in checks}


# ------------------------------------------------------------------ archival

def test_default_delete_archives_without_destroying_history(db):
    old, new = ingest(db, "I live in Mumbai.", "I moved to Pune.")
    graph_before = SqlGraphRepository(db).load()

    body = client.delete(f"/memory/{new.id}").json()
    assert body["mode"] == "archived"

    db.expire_all()
    archived = db.get(Memory, new.id)
    assert archived.state == "archived" and archived.is_contradicted is False
    # lineage, evidence and graph are all preserved
    rels = {(r.source_memory_id, r.target_memory_id, r.relationship_type) for r in db.query(MemoryRelationship)}
    assert (old.id, new.id, lineage.SUPERSEDED_BY) in rels
    assert decisions(db, new.id) == ["supersession", "archived_by_request"]
    assert SqlGraphRepository(db).load().edges == graph_before.edges

    # out of normal retrieval, still available for history/audit
    assert new.id not in {m.id for m, _ in retrieve_memories(db, "Where do I live?", limit=10)}
    assert new.id in {m.id for m, _ in retrieve_memories(db, "Where do I live?", limit=10, include_archived=True)}
    assert_no_dangling_references(db)


def test_archive_is_idempotent(db):
    (memory,) = ingest(db, "I live in Mumbai.")
    client.delete(f"/memory/{memory.id}")
    client.delete(f"/memory/{memory.id}")
    assert decisions(db, memory.id) == ["new", "archived_by_request"]


def test_delete_unknown_memory_is_404(db):
    assert client.delete("/memory/999999").status_code == 404
    assert client.delete("/memory/999999", params={"purge": "true"}).status_code == 404


# --------------------------------------------------------------------- purge

def test_purge_is_explicit_and_destructive(db):
    (memory,) = ingest(db, "I live in Ahmedabad.")
    memory_id = memory.id
    body = client.delete(f"/memory/{memory_id}", params={"purge": "true"}).json()
    assert body["mode"] == "purged"

    db.expire_all()
    assert db.get(Memory, memory_id) is None
    assert count(db, "SELECT count(*) FROM memory_evidence WHERE memory_id = :m", m=memory_id) == 0
    assert count(db, "SELECT count(*) FROM memory_entities WHERE memory_id = :m", m=memory_id) == 0
    assert "ahmedabad" not in {n.id for n in SqlGraphRepository(db).load().nodes}
    assert_no_dangling_references(db)


def test_purge_keeps_shared_and_aliased_entities(db):
    kept, purged = ingest(db, "Rahul Patel lives in Delhi.", "Rahul Patel works at BMW.")
    repo = SqlGraphRepository(db)
    bmw = repo.resolve("BMW")
    repo.add_alias(bmw, "Bayerische Motoren Werke")
    db.commit()

    client.delete(f"/memory/{purged.id}", params={"purge": "true"})
    db.expire_all()
    nodes = {n.id for n in SqlGraphRepository(db).load().nodes}
    assert "rahul patel" in nodes          # still mentioned by another memory
    assert "delhi" in nodes
    assert "bmw" in nodes                  # explicit alias keeps it
    edges = {(e.source, e.relationship, e.target) for e in SqlGraphRepository(db).load().edges}
    assert ("rahul patel", "works_at", "bmw") not in edges
    assert_no_dangling_references(db)


def test_purging_a_superseding_memory_records_the_lineage_loss(db):
    old, new = ingest(db, "I live in Mumbai.", "I moved to Pune.")
    old_id, new_id = old.id, new.id
    body = client.delete(f"/memory/{new_id}", params={"purge": "true"}).json()
    assert body["affected_memory_ids"] == [old_id]

    db.expire_all()
    assert db.query(MemoryRelationship).count() == 0
    ev = db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == old_id).order_by(MemoryEvidence.id).all()[-1]
    assert ev.decision == "lineage_removed_by_purge"
    assert ev.reason_codes == [f"purged_memory:{new_id}", "superseded_by:outgoing"]
    assert_no_dangling_references(db)


def test_purging_a_contradicting_memory_keeps_the_contradicted_claim_archived(db):
    old, new = ingest(db, "I live in Mumbai.", "I live in Pune.")
    old_id = old.id
    client.delete(f"/memory/{new.id}", params={"purge": "true"})

    db.expire_all()
    claim = db.get(Memory, old_id)
    assert (claim.state, claim.is_contradicted, claim.contradicted_by_id) == ("archived", True, None)
    assert decisions(db, old_id)[-1] == "lineage_removed_by_purge"
    assert_no_dangling_references(db)


def test_purging_a_plan_completion_records_the_fulfilled_link_loss(db):
    pipeline = MemoryPipeline(db)
    plan = pipeline.process("I will move to Bangalore.", "profile")["memory"]
    moved = pipeline.process("I moved to Bangalore.", "profile")["memory"]
    plan_id = plan.id
    client.delete(f"/memory/{moved.id}", params={"purge": "true"})

    db.expire_all()
    assert db.get(Memory, plan_id) is not None
    assert db.query(MemoryRelationship).filter(MemoryRelationship.relationship_type == lineage.FULFILLED_BY).count() == 0
    last = db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == plan_id).order_by(MemoryEvidence.id).all()[-1]
    assert "fulfilled_by:outgoing" in last.reason_codes
    assert_no_dangling_references(db)
