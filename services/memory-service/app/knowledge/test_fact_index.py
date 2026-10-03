"""
knowledge_facts index (PR-1): derived from memories.content, kept in sync in
the same transaction as content changes, rebuildable. Evolution reads it only
for candidate discovery (Section 2, see app/pipeline/test_structural_candidates.py);
decisions never depend on index contents alone.
"""

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError

import app.graph.graph_service as graph_service_module
from app.database import SessionLocal, engine
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.fact_index import (
    check,
    content_sha256,
    derive_fact_row,
    lookup_fact_rows,
    reindex,
)
from app.knowledge.fact_index_model import KnowledgeFactRow
from app.knowledge.knowledge_types import KnowledgeDecision
from app.main import app
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.provenance.models import EXTRACTOR_VERSION
from app.service import lock_memory
from app.testing_support import reset_database
from app.understanding.memory_parser import parse_memory

client = TestClient(app)

ROW_FIELDS = (
    "entity_key", "attribute_key", "value_key", "value_text", "fact_type", "single_valued",
    "temporal_state", "is_negated", "is_placeholder", "confidence", "content_sha256",
    "extractor_version",
)


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def row_for(db, memory_id):
    db.expire_all()
    return db.get(KnowledgeFactRow, memory_id)


def snapshot(db):
    db.expire_all()
    return {
        r.memory_id: tuple(getattr(r, f) for f in ROW_FIELDS)
        for r in db.query(KnowledgeFactRow).all()
    }


def ingest(db, *statements, category="profile"):
    pipeline = MemoryPipeline(db)
    return [pipeline.process(s, category) for s in statements]


# ------------------------------------------------------------- derivation

@pytest.mark.parametrize("statement", [
    "I live in Pune.",
    "I do not live in Mumbai anymore.",          # negated + HISTORICAL
    "I will move to Bangalore next month.",      # FUTURE
    "I used to live in Delhi.",                  # HISTORICAL
    "I like coffee.",                            # multi-valued
    "My friend Rahul works at Google.",          # non-user entity
    "I use my MacBook Air for development.",     # direct-object value
])
def test_row_fields_exactly_match_extractor_output(db, statement):
    (result,) = ingest(db, statement)
    fact = extract_fact(parse_memory(statement))
    row = row_for(db, result["memory"].id)
    assert row is not None
    assert (row.entity_key, row.attribute_key, row.value_key) == (
        fact.entity.strip().lower(), fact.attribute.strip().lower(), fact.value.strip().lower(),
    )
    assert row.value_text == fact.value
    assert (row.fact_type, row.temporal_state, row.is_negated, row.confidence) == (
        fact.fact_type, fact.temporal_state, fact.is_negated, fact.confidence,
    )
    assert row.is_placeholder is False
    assert row.content_sha256 == content_sha256(result["memory"].content)
    assert row.extractor_version == EXTRACTOR_VERSION


def test_new_memory_gets_correct_row(db):
    (result,) = ingest(db, "I live in Pune.")
    row = row_for(db, result["memory"].id)
    assert (row.entity_key, row.attribute_key, row.value_key) == ("user", "residence", "pune")
    assert (row.temporal_state, row.single_valued, row.is_negated) == ("CURRENT", True, False)


@pytest.mark.parametrize("statement", ["Wow.", "Some random general statement."])
def test_memory_without_usable_fact_has_no_row(db, statement):
    """No fact, or the extractor's no-attribute marker ('general') -> no row."""
    (result,) = ingest(db, statement, category="fact")
    assert derive_fact_row(statement) is None
    assert row_for(db, result["memory"].id) is None


def test_overlong_keys_are_never_truncated(db):
    long_value = "Zyx" + "a" * 300
    assert derive_fact_row(f"I live in {long_value}.") is None


# ------------------------------------------------------------ placeholders

@pytest.mark.parametrize("statement, value_key", [("I live there.", "unknown"), ("I like it.", "it")])
def test_placeholder_facts_are_flagged_and_excluded_from_lookup(db, statement, value_key):
    (result,) = ingest(db, statement)
    row = row_for(db, result["memory"].id)
    assert row.is_placeholder is True and row.value_key == value_key
    entity, attribute = row.entity_key, row.attribute_key
    assert lookup_fact_rows(db, entity, attribute) == []
    assert [r.memory_id for r in lookup_fact_rows(db, entity, attribute, include_placeholders=True)] == [
        result["memory"].id
    ]


def test_lookup_returns_real_facts_by_domain_and_value(db):
    results = ingest(db, "I live in Pune.", "I like coffee.", "I like tea.")
    pune, coffee, tea = (r["memory"].id for r in results)
    assert [r.memory_id for r in lookup_fact_rows(db, "user", "residence")] == [pune]
    assert [r.memory_id for r in lookup_fact_rows(db, "User", "Preference")] == [coffee, tea]
    assert [r.memory_id for r in lookup_fact_rows(db, "user", "preference", "Tea")] == [tea]


# --------------------------------------------------------------- lifecycle

def test_reinforcement_does_not_duplicate_rows(db):
    first, second = ingest(db, "I live in Pune.", "I live in Pune.")
    assert second["knowledge"].decision == KnowledgeDecision.REINFORCEMENT
    assert first["memory"].id == second["memory"].id
    assert db.query(KnowledgeFactRow).count() == 1


def test_merge_rewrites_canonical_row_to_merged_content(db):
    first, merged = ingest(db, "I use a MacBook Air.", "I use my MacBook Air for development.", category="fact")
    assert merged["knowledge"].decision == KnowledgeDecision.MERGE
    row = row_for(db, first["memory"].id)
    assert row.content_sha256 == content_sha256("I use my MacBook Air for development.")
    assert db.query(KnowledgeFactRow).count() == 1


def test_contradiction_and_supersession_keep_rows_lifecycle_is_not_copied(db):
    mumbai, pune = ingest(db, "I live in Mumbai.", "I live in Pune.")
    delhi = ingest(db, "I moved to Delhi.")[0]
    db.expire_all()
    assert db.get(Memory, mumbai["memory"].id).state == "archived"
    # rows exist for archived and superseded memories; no lifecycle columns
    assert {r.memory_id for r in db.query(KnowledgeFactRow)} == {
        mumbai["memory"].id, pune["memory"].id, delhi["memory"].id,
    }
    columns = set(KnowledgeFactRow.__table__.columns.keys())
    assert not columns & {"state", "is_contradicted", "contradicted_by_id", "superseded_by_id", "valid_to"}


def test_archive_keeps_row_and_purge_removes_it(db):
    (result,) = ingest(db, "I live in Pune.")
    memory_id = result["memory"].id
    assert client.delete(f"/memory/{memory_id}").json()["mode"] == "archived"
    assert row_for(db, memory_id) is not None
    assert client.delete(f"/memory/{memory_id}", params={"purge": "true"}).json()["mode"] == "purged"
    assert row_for(db, memory_id) is None
    assert db.execute(text(
        "SELECT count(*) FROM knowledge_facts f WHERE NOT EXISTS (SELECT 1 FROM memories m WHERE m.id = f.memory_id)"
    )).scalar() == 0


# ------------------------------------------------------------------ PUT

def test_put_replaces_derived_row(db):
    (result,) = ingest(db, "I live in Mumbai.")
    memory_id = result["memory"].id
    assert client.put(f"/memory/{memory_id}", json={"content": "I work at BMW."}).status_code == 200
    row = row_for(db, memory_id)
    assert (row.entity_key, row.attribute_key, row.value_key) == ("user", "employer", "bmw")
    assert row.content_sha256 == content_sha256("I work at BMW.")
    assert lookup_fact_rows(db, "user", "residence") == []


def test_put_to_text_without_fact_deletes_row(db):
    (result,) = ingest(db, "I live in Mumbai.")
    memory_id = result["memory"].id
    client.put(f"/memory/{memory_id}", json={"content": "Wow."})
    assert row_for(db, memory_id) is None


def test_failed_put_leaves_content_and_row_consistent(db, monkeypatch):
    (result,) = ingest(db, "I live in Mumbai.")
    memory_id = result["memory"].id
    before = snapshot(db)

    def boom(self, parsed, mid):
        raise RuntimeError("simulated failure after the fact row was written")

    monkeypatch.setattr(graph_service_module.GraphService, "persist_memory", boom)
    with pytest.raises(RuntimeError):
        client.put(f"/memory/{memory_id}", json={"content": "I work at BMW."})
    db.expire_all()
    assert db.get(Memory, memory_id).content == "I live in Mumbai."
    assert snapshot(db) == before


def test_failed_evolution_leaves_no_fact_row(db, monkeypatch):
    def boom(self, parsed, mid):
        raise RuntimeError("simulated failure after the fact row was written")

    monkeypatch.setattr(graph_service_module.GraphService, "persist_memory", boom)
    with pytest.raises(RuntimeError):
        MemoryPipeline(db).process("I live in Pune.", "profile")
    db.expire_all()
    assert db.query(Memory).count() == 0
    assert db.query(KnowledgeFactRow).count() == 0


def test_concurrent_puts_leave_row_matching_final_content(db):
    (result,) = ingest(db, "I live in Mumbai.")
    memory_id = result["memory"].id
    barrier = threading.Barrier(2)

    def put(text_):
        barrier.wait()
        client.put(f"/memory/{memory_id}", json={"content": text_})

    threads = [threading.Thread(target=put, args=(t,)) for t in ("I live in Goa.", "I work at BMW.")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    db.expire_all()
    final = db.get(Memory, memory_id).content
    assert row_for(db, memory_id).content_sha256 == content_sha256(final)
    assert check(db)["consistent"]


# ---------------------------------------------------------- rebuild/backfill

def test_rebuild_reproduces_incremental_population(db):
    ingest(db, "I live in Mumbai.", "I live in Pune.", "I moved to Delhi.", "I will move to Goa.",
           "I like coffee.", "I live there.", "Wow.", "My friend Rahul works at Google.")
    incremental = snapshot(db)
    assert incremental
    db.execute(text("DELETE FROM knowledge_facts"))
    db.commit()
    stats = reindex(SessionLocal, rebuild_all=True)
    assert stats["skipped_locked"] == 0
    assert snapshot(db) == incremental


def test_backfill_existing_memories_is_idempotent_and_read_only(db):
    statements = ["I live in Pune.", "I like tea.", "Wow.", "I live there."]
    db.add_all([Memory(content=s, category="fact", state="active") for s in statements])
    db.commit()
    memories_before = [(m.id, m.content, m.version, m.state) for m in db.query(Memory).order_by(Memory.id)]

    report = check(db)
    assert not report["consistent"] and len(report["missing"]) == 3

    first = reindex(SessionLocal)
    assert first["written"] == 3
    assert check(db)["consistent"]
    second = reindex(SessionLocal)
    assert second["written"] == 0 and second["deleted"] == 0

    db.expire_all()
    assert [(m.id, m.content, m.version, m.state) for m in db.query(Memory).order_by(Memory.id)] == memories_before


def test_check_detects_stale_and_unexpected_rows_and_reindex_repairs_them(db):
    pune, wow = (r["memory"].id for r in ingest(db, "I live in Pune.", "Wow."))
    # change content behind the index's back (not via PUT)
    db.execute(text("UPDATE memories SET content = 'I live in Goa.' WHERE id = :i"), {"i": pune})
    db.execute(text("UPDATE memories SET content = 'I like tea.' WHERE id = :i"), {"i": wow})
    db.commit()
    report = check(db)
    assert report["stale"] == [pune] and report["missing"] == [wow]

    reindex(SessionLocal)
    assert check(db)["consistent"]
    assert row_for(db, pune).value_key == "goa"


def test_reindex_skips_rows_locked_by_a_live_writer(db):
    db.add(Memory(content="I live in Pune.", category="fact", state="active"))
    db.commit()
    memory_id = db.query(Memory).one().id

    holder = SessionLocal()
    lock_memory(holder, holder.get(Memory, memory_id))
    try:
        stats = {}
        worker = threading.Thread(target=lambda: stats.update(reindex(SessionLocal)))
        worker.start()
        worker.join(timeout=60)
        assert stats["skipped_locked"] == 1 and stats["written"] == 0
    finally:
        holder.rollback()
        holder.close()
    assert reindex(SessionLocal)["written"] == 1


# ------------------------------------------------------------- constraints

@pytest.mark.parametrize("override, constraint", [
    ({"memory_id": 999999}, "fk_knowledge_facts_memory"),
    ({"temporal_state": "SOMETIME"}, "ck_knowledge_facts_temporal_state"),
    ({"entity_key": ""}, "ck_knowledge_facts_keys_not_empty"),
    ({"attribute_key": ""}, "ck_knowledge_facts_keys_not_empty"),
    ({"content_sha256": "abc"}, "ck_knowledge_facts_content_sha256"),
])
def test_database_constraints(db, override, constraint):
    (no_fact,) = ingest(db, "Wow.", category="fact")  # a memory without a row
    values = dict(
        memory_id=no_fact["memory"].id, entity_key="user", attribute_key="residence",
        value_key="x", value_text="x", fact_type="LOCATION", single_valued=True,
        temporal_state="CURRENT", is_negated=False, is_placeholder=False, confidence=0.9,
        content_sha256="0" * 64, extractor_version="v",
    )
    values.update(override)
    with pytest.raises(IntegrityError, match=constraint):
        db.execute(KnowledgeFactRow.__table__.insert().values(**values))
    db.rollback()


def test_at_most_one_row_per_memory(db):
    (result,) = ingest(db, "I live in Pune.")
    with pytest.raises(IntegrityError, match="knowledge_facts_pkey"):
        db.execute(KnowledgeFactRow.__table__.insert().values(
            memory_id=result["memory"].id, entity_key="user", attribute_key="residence",
            value_key="goa", value_text="Goa", fact_type="LOCATION", single_valued=True,
            temporal_state="CURRENT", is_negated=False, is_placeholder=False, confidence=0.9,
            content_sha256="0" * 64, extractor_version="v",
        ))
    db.rollback()


# ------------------------------------- discovery only, never a decision

def _statements_touching_facts(run):
    seen = []

    def listener(conn, cursor, statement, parameters, context, executemany):
        if "knowledge_facts" in statement:
            seen.append(statement.split()[0].upper())

    event.listen(engine, "before_cursor_execute", listener)
    try:
        run()
    finally:
        event.remove(engine, "before_cursor_execute", listener)
    return seen


def test_evolution_reads_the_fact_index_only_for_candidate_discovery(db):
    # Section 2: evolution SELECTs candidates from the index; the index is
    # still written only by sync_memory_fact (INSERT ... ON CONFLICT / DELETE).
    ingest(db, "I live in Mumbai.")
    pipeline = MemoryPipeline(db)
    statements = _statements_touching_facts(lambda: [
        pipeline.process(s, "profile")
        for s in ("I live in Pune.", "I moved to Delhi.", "I live in Delhi.", "I like tea.", "I will move to Goa.")
    ])
    assert "INSERT" in statements, "the pipeline must write the index"
    assert "SELECT" in statements, "evolution must consult the index for candidates"
    assert set(statements) <= {"SELECT", "INSERT", "DELETE"}, statements


def test_evolution_decisions_do_not_depend_on_the_fact_index(db):
    """Same decisions with a clean index, an empty index, and a poisoned index."""
    script = ["I live in Mumbai.", "I like coffee.", "I live in Pune.", "I moved to Delhi.",
              "I will move to Goa.", "I like coffee.", "I live there."]

    def run(prepare):
        reset_database()
        session = SessionLocal()
        try:
            pipeline = MemoryPipeline(session)
            decisions = []
            for i, statement in enumerate(script):
                prepare(session, i)
                result = pipeline.process(statement, "profile")
                decisions.append((result["knowledge"].decision.value, tuple(result["reason_codes"])))
            return decisions
        finally:
            session.close()

    def nothing(session, i):
        pass

    def empty_index(session, i):
        session.execute(text("DELETE FROM knowledge_facts"))
        session.commit()

    def poisoned_index(session, i):
        # Every existing memory claims a conflicting residence in the index.
        session.execute(text(
            "UPDATE knowledge_facts SET entity_key = 'user', attribute_key = 'residence', "
            "value_key = 'atlantis', temporal_state = 'CURRENT', single_valued = true, is_placeholder = false"
        ))
        session.commit()

    def normalized(decisions):
        # memory ids differ between runs only by sequence offsets; compare shapes
        return [(d, tuple(code.split(":")[0] for code in codes)) for d, codes in decisions]

    clean = normalized(run(nothing))
    assert normalized(run(empty_index)) == clean
    assert normalized(run(poisoned_index)) == clean
