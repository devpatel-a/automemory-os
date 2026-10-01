"""
Provenance is first-class, append-only, and never fabricated.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import app.pipeline.memory_pipeline as pipeline_module
from app.database import SessionLocal
from app.main import app
from app.pipeline.memory_pipeline import MemoryPipeline
from app.provenance.models import EXTRACTOR_VERSION, MemoryEvidence, Provenance
from app.testing_support import reset_database


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def evidence_for(db, memory_id):
    db.expire_all()
    return db.query(MemoryEvidence).filter(MemoryEvidence.memory_id == memory_id).order_by(MemoryEvidence.id).all()


def test_pipeline_records_evidence_with_caller_provenance(db):
    observed = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    result = MemoryPipeline(db).process(
        "I live in Pune.", "profile",
        provenance=Provenance(source_type="chat", conversation_id="c-7", message_id="m-1842", observed_at=observed),
    )
    (ev,) = evidence_for(db, result["memory"].id)
    assert (ev.source_type, ev.conversation_id, ev.message_id) == ("chat", "c-7", "m-1842")
    assert ev.observed_at == observed
    assert ev.raw_text == "I live in Pune."
    assert ev.extraction_method == "deterministic_nlp"
    assert ev.extractor_version == EXTRACTOR_VERSION
    assert ev.confidence == result["knowledge"].fact.confidence
    assert ev.decision == "new"
    assert ev.reason_codes == ["no_candidates"]


def test_merge_keeps_every_original_statement_recoverable(db):
    pipeline = MemoryPipeline(db)
    first = pipeline.process("I use a MacBook Air.", "fact")["memory"]
    merged = pipeline.process("I use my MacBook Air for development.", "fact")
    assert merged["memory"].id == first.id
    raw = [e.raw_text for e in evidence_for(db, first.id)]
    assert raw == ["I use a MacBook Air.", "I use my MacBook Air for development."]
    assert [e.decision for e in evidence_for(db, first.id)] == ["new", "merge"]


def test_reinforcement_appends_evidence(db):
    pipeline = MemoryPipeline(db)
    memory = pipeline.process("I live in Pune.", "fact")["memory"]
    pipeline.process("I live in Pune.", "fact", provenance=Provenance(message_id="m-2"))
    evidence = evidence_for(db, memory.id)
    assert len(evidence) == 2
    assert evidence[1].decision == "reinforcement" and evidence[1].message_id == "m-2"


def test_evidence_is_rolled_back_with_a_failed_evolution(db, monkeypatch):
    MemoryPipeline(db).process("I live in Mumbai.", "profile")

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(pipeline_module, "contradict_existing_memory", boom)
    with pytest.raises(RuntimeError):
        MemoryPipeline(db).process("I live in Pune.", "profile")
    db.expire_all()
    assert db.query(MemoryEvidence).count() == 1


def test_evidence_endpoint_explains_contradiction_and_supersession(db):
    client = TestClient(app)
    old = client.post("/memory", json={
        "content": "I live in Mumbai.", "category": "profile",
        "source_type": "chat", "message_id": "m-1",
    }).json()
    new = client.post("/memory", json={"content": "I live in Pune.", "category": "profile", "message_id": "m-2"}).json()

    body = client.get(f"/memory/{old['id']}/evidence").json()
    assert body["memory"]["is_contradicted"] is True
    assert body["contradicted_by"] == {"relationship_type": "contradicted_by", "memory_id": new["id"], "content": "I live in Pune."}
    assert body["evidence"][0]["message_id"] == "m-1"
    assert body["evidence"][0]["source_type"] == "chat"

    moved = client.post("/memory", json={"content": "I moved to Delhi.", "category": "profile"}).json()
    new_body = client.get(f"/memory/{new['id']}/evidence").json()
    assert {"relationship_type": "superseded_by", "memory_id": moved["id"], "content": "I moved to Delhi."} in new_body["outgoing"]
    assert "transition_detected" in client.get(f"/memory/{moved['id']}/evidence").json()["evidence"][0]["reason_codes"]

    assert client.get("/memory/999999/evidence").status_code == 404


def test_pipeline_endpoint_returns_reason_codes(db):
    client = TestClient(app)
    client.post("/pipeline/process", params={"content": "I live in Mumbai.", "category": "profile"})
    body = client.post("/pipeline/process", params={"content": "I live in Pune.", "category": "profile"}).json()
    assert body["knowledge_decision"] == "contradiction"
    assert "conflicting_current_claims" in body["reason_codes"]
    assert body["action"] == "archive"  # backward-compatible field unchanged
