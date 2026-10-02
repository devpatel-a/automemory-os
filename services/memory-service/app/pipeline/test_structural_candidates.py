"""
Section 2: structural candidate discovery (knowledge_facts) in evolution.

The index NOMINATES live memories in the incoming fact's domain; every
nominee is re-validated against its canonical memory, and the existing
classifier decides. These tests show:
- a conflicting fact outside the semantic top-5 is now found and handled by
  the SAME rule as when semantic search finds it (A, D);
- candidates are the union of both sources, each memory once (B);
- placeholders and questions never nominate or get nominated (C);
- a missing, stale or poisoned index can only lose recall, never corrupt
  canonical state (E);
- the existing locking / version / retry model covers structural targets (F).

"Far" scenarios assert as a precondition that the existing memory really is
outside the semantic top-CANDIDATE_LIMIT for the incoming statement.
"""

import threading

import pytest
from sqlalchemy import text

import app.pipeline.memory_pipeline as pipeline_module
from app import lineage
from app.database import SessionLocal
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.fact_index import check, reindex, structural_candidates, sync_memory_fact
from app.knowledge.knowledge_types import KnowledgeDecision
from app.models import Memory
from app.pipeline.memory_pipeline import CANDIDATE_LIMIT, MemoryPipeline
from app.semantic.semantic_service import semantic_search
from app.service import archive_memory, bump_version, create_memory, lock_memory
from app.testing_support import reset_database
from app.understanding.memory_parser import parse_memory

WHO = ["My sister", "My brother", "My friend", "My colleague", "My cousin", "My manager",
       "My boss", "My partner", "Rahul", "Priya", "My daughter", "My son"]
LIVES_IN_PUNE = [f"{w} lives in Pune." for w in WHO]
MOVED_TO_PUNE = [f"{w} moved to Pune." for w in WHO]
WORKS_AT_MICROSOFT = [f"{w} works at Microsoft." for w in WHO]
NOT_MUMBAI = ["I do not visit Mumbai anymore.", "I do not travel to Mumbai anymore.",
              "I do not drive in Mumbai anymore.", "I do not shop in Mumbai anymore.",
              "I no longer commute to Mumbai.", "I do not party in Mumbai anymore.",
              "I do not eat out in Mumbai anymore.", "I do not fly to Mumbai anymore.",
              "I do not teach in Mumbai anymore.", "I do not swim in Mumbai anymore."]
NOT_COFFEE = ["I do not buy coffee anymore.", "I do not brew coffee anymore.",
              "I do not make coffee anymore.", "I do not order coffee anymore.",
              "I do not sell coffee anymore.", "I do not need coffee anymore.",
              "I do not want coffee anymore.", "I do not drink coffee anymore.",
              "I do not grind coffee anymore.", "I do not roast coffee anymore."]
GOA = [f"{w} lives in Goa." for w in WHO] + [
    "I visited Goa.", "I travel to Goa often.", "I bought a house in Goa.",
    "I have friends in Goa.", "I holidayed in Goa."]


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def process(db, statement):
    return MemoryPipeline(db).process(statement, "profile")


def semantic_rank(db, memory_id, query):
    ranked = [m.id for m, _ in semantic_search(db, query, limit=1000)]
    return ranked.index(memory_id) + 1


def seed(db, existing, distractors, incoming):
    """Store `existing`, then distractors; assert it is outside the semantic top-K."""
    existing_id = process(db, existing)["memory"].id
    for statement in distractors:
        process(db, statement)
    rank = semantic_rank(db, existing_id, incoming)
    assert rank > CANDIDATE_LIMIT, f"precondition: {existing!r} ranks {rank} for {incoming!r}"
    return existing_id


def fact_of(statement):
    return extract_fact(parse_memory(statement))


def live_user_residences(db):
    db.expire_all()
    historical = lineage.historical_memory_ids(db, [m.id for m in db.query(Memory)])
    out = []
    for m in db.query(Memory).filter(Memory.state != "archived").order_by(Memory.id):
        f = fact_of(m.content)
        if (f and (f.entity, f.attribute) == ("user", "residence") and f.temporal_state == "CURRENT"
                and not f.is_negated and m.id not in historical):
            out.append(m.content)
    return out


# ------------------------------------------------ A. original top-5 failure

def test_conflict_outside_semantic_top5_is_contradicted(db):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")

    result = process(db, "I live in Pune.")

    knowledge = result["knowledge"]
    assert knowledge.decision == KnowledgeDecision.CONTRADICTION
    assert knowledge.target_memory_id == mumbai
    assert f"structural_candidate:{mumbai}" in result["reason_codes"]
    assert f"contradicted_memory:{mumbai}" in result["reason_codes"]
    db.expire_all()
    loser = db.get(Memory, mumbai)
    assert loser.state == "archived" and loser.is_contradicted
    assert loser.contradicted_by_id == result["memory"].id
    assert live_user_residences(db) == ["I live in Pune."]


def test_without_structural_discovery_the_original_failure_reproduces(db, monkeypatch):
    # Control: the same scenario with structural discovery disabled (limit 0)
    # is the pre-Section-2 behaviour: the conflict is missed, two residences live.
    monkeypatch.setattr(pipeline_module, "STRUCTURAL_CANDIDATE_LIMIT", 0)
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")

    result = process(db, "I live in Pune.")

    assert result["knowledge"].decision != KnowledgeDecision.CONTRADICTION
    assert db.get(Memory, mumbai).state == "active"
    assert live_user_residences(db) == ["I live in Mumbai.", "I live in Pune."]


# --------------------------- D. same decision whether found semantically or structurally

PARITY = [
    # existing,                 incoming,                           distractors,       decision
    ("I live in Mumbai.", "I live in Pune.", LIVES_IN_PUNE, KnowledgeDecision.CONTRADICTION),
    ("I live in Mumbai.", "I moved to Pune.", MOVED_TO_PUNE, KnowledgeDecision.SUPERSESSION),
    # existing extracted-HISTORICAL + incoming CURRENT (Rule B)
    ("I used to live in Delhi.", "I live in Pune.", LIVES_IN_PUNE, KnowledgeDecision.SUPERSESSION),
    # negation of the same value (Rule G), single- and multi-valued
    ("I live in Mumbai.", "I do not live in Mumbai anymore.", NOT_MUMBAI, KnowledgeDecision.SUPERSESSION),
    ("I like coffee.", "I do not like coffee anymore.", NOT_COFFEE, KnowledgeDecision.SUPERSESSION),
    ("I work at Google.", "I work at Microsoft.", WORKS_AT_MICROSOFT, KnowledgeDecision.CONTRADICTION),
]


def _outcome(db, existing_id, result):
    db.expire_all()
    existing = db.get(Memory, existing_id)
    superseded = existing_id in lineage.historical_memory_ids(db, [existing_id])
    return (result["knowledge"].decision, result["knowledge"].target_memory_id == existing_id,
            existing.state, existing.is_contradicted, superseded)


@pytest.mark.parametrize("existing, incoming, distractors, decision", PARITY)
def test_structural_target_gets_the_same_decision_as_a_semantic_one(existing, incoming, distractors, decision):
    reset_database()
    session = SessionLocal()
    try:
        near_id = process(session, existing)["memory"].id
        assert semantic_rank(session, near_id, incoming) <= CANDIDATE_LIMIT
        near = _outcome(session, near_id, process(session, incoming))
    finally:
        session.close()

    reset_database()
    session = SessionLocal()
    try:
        far_id = seed(session, existing, distractors, incoming)
        result = process(session, incoming)
        far = _outcome(session, far_id, result)
        assert f"structural_candidate:{far_id}" in result["reason_codes"]
    finally:
        session.close()

    assert near == far
    assert far[:2] == (decision, True)


@pytest.mark.parametrize("existing, incoming, distractors", [
    # a past residence never overrides the current one
    ("I live in Mumbai.", "I used to live in Delhi.", [f"{w} used to live in Delhi." for w in WHO]),
    # a plan never overrides the current one
    ("I live in Mumbai.", "I will move to Goa.", [f"{w} will move to Goa." for w in WHO]),
    # a plan is never contradicted/superseded
    ("I will move to Goa.", "I live in Pune.", LIVES_IN_PUNE),
])
def test_far_memories_keep_temporal_semantics(db, existing, incoming, distractors):
    existing_id = seed(db, existing, distractors, incoming)

    result = process(db, incoming)

    assert result["knowledge"].target_memory_id != existing_id
    assert result["knowledge"].decision not in (
        KnowledgeDecision.CONTRADICTION, KnowledgeDecision.SUPERSESSION, KnowledgeDecision.MERGE,
    )
    db.expire_all()
    kept = db.get(Memory, existing_id)
    assert (kept.content, kept.state, kept.is_contradicted) == (existing, "active", False)
    assert existing_id not in lineage.historical_memory_ids(db, [existing_id])


def test_far_plan_is_fulfilled_and_then_never_a_candidate_again(db):
    plan = seed(db, "I will move to Goa.", GOA, "I live in Goa.")

    result = process(db, "I live in Goa.")

    assert f"fulfilled_plan:{plan}" in result["reason_codes"]
    db.expire_all()
    assert plan in lineage.historical_memory_ids(db, [plan])
    assert db.get(Memory, plan).state == "active"   # kept for history
    # A fulfilled plan is historical: no longer a structural candidate.
    lookup = structural_candidates(db, fact_of("I will move to Goa."), 50)
    assert plan not in [m.id for m in lookup.memories]


def test_superseded_far_memory_is_not_targeted_again(db):
    mumbai = seed(db, "I live in Mumbai.", MOVED_TO_PUNE, "I moved to Pune.")
    pune = process(db, "I moved to Pune.")["memory"].id
    assert mumbai in lineage.historical_memory_ids(db, [mumbai])

    result = process(db, "I live in Delhi.")

    # The live current residence (Pune) is the conflict; Mumbai is history.
    assert result["knowledge"].target_memory_id == pune
    db.expire_all()
    assert db.get(Memory, mumbai).state == "active" and not db.get(Memory, mumbai).is_contradicted


# ---------------------------------------------- B. structural + semantic union

def test_candidates_are_the_union_in_semantic_then_structural_order(db, monkeypatch):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
    near = process(db, "I used to live in Pune.")["memory"].id   # in the domain AND semantically close
    captured = {}
    original = pipeline_module.process_knowledge

    def spy(parsed, candidates, historical):
        captured["ids"] = [(c[0].id, c[1] is None) for c in candidates]
        return original(parsed, candidates, historical)

    monkeypatch.setattr(pipeline_module, "process_knowledge", spy)
    pipeline = MemoryPipeline(db)
    pipeline.process("I live in Pune.", "profile")

    ids = [mid for mid, _ in captured["ids"]]
    assert len(ids) == len(set(ids)), "each memory appears once"
    semantic = [mid for mid, no_distance in captured["ids"] if not no_distance]
    structural_only = [mid for mid, no_distance in captured["ids"] if no_distance]
    assert ids == semantic + structural_only, "semantic ranking first, unchanged"
    assert len(semantic) == CANDIDATE_LIMIT
    assert near in semantic and pipeline._candidate_sources[near] == {"semantic", "structural"}
    assert structural_only == [mumbai] and pipeline._candidate_sources[mumbai] == {"structural"}


def test_lookup_is_deterministic_and_bounded(db):
    ids = [create_memory(content=c, category="profile", db=db, semantic_dedupe=False).id
           for c in ("I used to live in Delhi.", "I used to live in Agra.", "I used to live in Surat.")]
    for mid in ids:
        sync_memory_fact(db, db.get(Memory, mid))
    db.commit()
    fact = fact_of("I live in Pune.")

    full = structural_candidates(db, fact, 50)
    assert [m.id for m in full.memories] == sorted(ids, reverse=True) and not full.truncated
    capped = structural_candidates(db, fact, 2)
    assert [m.id for m in capped.memories] == sorted(ids, reverse=True)[:2] and capped.truncated
    assert structural_candidates(db, fact, 0).memories == []


def test_truncation_is_reported_never_silent(db, monkeypatch):
    for city in ("Delhi", "Agra", "Surat"):
        process(db, f"I used to live in {city}.")
    monkeypatch.setattr(pipeline_module, "STRUCTURAL_CANDIDATE_LIMIT", 1)

    result = process(db, "I live in Pune.")

    assert "structural_candidates_truncated" in result["reason_codes"]
    db.expire_all()
    evidence = db.execute(text(
        "SELECT reason_codes FROM memory_evidence WHERE memory_id = :i ORDER BY id DESC LIMIT 1"
    ), {"i": result["memory"].id}).scalar_one()
    assert "structural_candidates_truncated" in evidence


def test_multi_valued_lookup_uses_the_exact_value(db):
    tea, coffee = (process(db, s)["memory"].id for s in ("I like tea.", "I like coffee."))
    lookup = structural_candidates(db, fact_of("I like coffee."), 50)
    assert [m.id for m in lookup.memories] == [coffee]
    assert tea not in [m.id for m in structural_candidates(db, fact_of("I like juice."), 50).memories]


# ------------------------------------------------- C. placeholders / questions

def test_placeholder_rows_are_never_nominated(db):
    there = process(db, "I live there.")["memory"].id
    lookup = structural_candidates(db, fact_of("I live in Pune."), 50)
    assert there not in [m.id for m in lookup.memories]
    # even if its row is corrupted to look real, canonical content rejects it
    db.execute(text("UPDATE knowledge_facts SET is_placeholder = false, value_key = 'goa' WHERE memory_id = :i"),
               {"i": there})
    db.commit()
    lookup = structural_candidates(db, fact_of("I live in Pune."), 50)
    assert there not in [m.id for m in lookup.memories] and lookup.rejected_ids == [there]


@pytest.mark.parametrize("incoming", ["I live there.", "I moved there.", "We live in Pune.", "Do I live in Pune?"])
def test_placeholder_or_question_statements_do_not_look_up(db, incoming):
    process(db, "I live in Mumbai.")
    assert structural_candidates(db, fact_of(incoming), 50).memories == []


def test_placeholder_statement_does_not_reach_a_far_fact(db):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE + MOVED_TO_PUNE, "I moved there.")
    result = process(db, "I moved there.")
    assert result["knowledge"].target_memory_id != mumbai
    db.expire_all()
    assert db.get(Memory, mumbai).state == "active"
    assert mumbai not in lineage.historical_memory_ids(db, [mumbai])


# ------------------------------------------------------------ E. index integrity

def test_missing_row_degrades_to_semantic_and_reindex_restores_recall(db):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
    db.execute(text("DELETE FROM knowledge_facts WHERE memory_id = :i"), {"i": mumbai})
    db.commit()
    assert check(db)["missing"] == [mumbai]
    assert mumbai not in [m.id for m in structural_candidates(db, fact_of("I live in Pune."), 50).memories]

    reindex(SessionLocal)
    assert check(db)["consistent"]
    result = process(db, "I live in Pune.")
    assert result["knowledge"].target_memory_id == mumbai
    assert result["knowledge"].decision == KnowledgeDecision.CONTRADICTION


def test_stale_row_is_validated_against_current_content(db):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
    # Content changed behind the index's back, out of the residence domain.
    db.execute(text("UPDATE memories SET content = 'I like tea.' WHERE id = :i"), {"i": mumbai})
    db.commit()
    assert check(db)["stale"] == [mumbai]

    lookup = structural_candidates(db, fact_of("I live in Pune."), 50)
    assert mumbai not in [m.id for m in lookup.memories] and mumbai in lookup.rejected_ids
    result = process(db, "I live in Pune.")
    assert result["knowledge"].target_memory_id != mumbai
    db.expire_all()
    assert (db.get(Memory, mumbai).content, db.get(Memory, mumbai).state) == ("I like tea.", "active")


def test_stale_row_whose_content_is_still_in_the_domain_is_used(db):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
    db.execute(text("UPDATE knowledge_facts SET extractor_version = 'old', content_sha256 = :h "
                    "WHERE memory_id = :i"), {"i": mumbai, "h": "0" * 64})
    db.commit()
    assert check(db)["stale"] == [mumbai]
    assert process(db, "I live in Pune.")["knowledge"].target_memory_id == mumbai


def test_poisoned_index_cannot_mutate_unrelated_memories(db):
    tea = process(db, "I like tea.")["memory"].id
    google = process(db, "My sister works at Google.")["memory"].id
    # Every row now claims to be the user's current residence "pune".
    db.execute(text(
        "UPDATE knowledge_facts SET entity_key = 'user', attribute_key = 'residence', value_key = 'pune', "
        "value_text = 'Pune', temporal_state = 'CURRENT', single_valued = true, is_placeholder = false"
    ))
    db.commit()
    before = {m.id: (m.content, m.state, m.version, m.is_contradicted) for m in db.query(Memory)}

    lookup = structural_candidates(db, fact_of("I live in Delhi."), 50)
    assert lookup.memories == [] and sorted(lookup.rejected_ids) == sorted([tea, google])
    result = process(db, "I live in Delhi.")

    assert result["knowledge"].decision not in (
        KnowledgeDecision.CONTRADICTION, KnowledgeDecision.SUPERSESSION, KnowledgeDecision.MERGE,
    )
    db.expire_all()
    after = {mid: (m.content, m.state, m.version, m.is_contradicted)
             for mid, m in ((mid, db.get(Memory, mid)) for mid in before)}
    assert after == before
    assert lineage.historical_memory_ids(db, list(before)) == set()
    reindex(SessionLocal, rebuild_all=True)
    assert check(db)["consistent"]


def test_archived_and_contradicted_memories_are_never_nominated(db):
    mumbai = process(db, "I live in Mumbai.")["memory"].id
    delhi = process(db, "I live in Delhi.")["memory"].id      # contradicts Mumbai
    db.expire_all()
    assert db.get(Memory, mumbai).is_contradicted
    archive_memory(delhi)
    assert structural_candidates(db, fact_of("I live in Pune."), 50).memories == []


# -------------------------------------------------------------- F. concurrency

def _spy_after_first_classification(monkeypatch, action):
    original = pipeline_module.process_knowledge
    calls = {"n": 0}

    def spy(*args, **kwargs):
        result = original(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 1:
            action()
        return result

    monkeypatch.setattr(pipeline_module, "process_knowledge", spy)
    return calls


def test_structural_target_edited_after_classification_is_reclassified(db, monkeypatch):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")

    def edit():
        other = SessionLocal()
        try:
            m = lock_memory(other, other.get(Memory, mumbai))
            m.content = "I like tea."   # index row now stale (not synced)
            bump_version(m)
            other.commit()
        finally:
            other.close()

    calls = _spy_after_first_classification(monkeypatch, edit)
    result = process(db, "I live in Pune.")

    assert calls["n"] == 2   # stale target rejected by the version check, then reclassified
    assert result["knowledge"].target_memory_id != mumbai
    db.expire_all()
    edited = db.get(Memory, mumbai)
    assert (edited.content, edited.state, edited.is_contradicted) == ("I like tea.", "active", False)


def test_structural_target_archived_after_classification_is_not_evolved(db, monkeypatch):
    mumbai = seed(db, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
    calls = _spy_after_first_classification(monkeypatch, lambda: archive_memory(mumbai))

    result = process(db, "I live in Pune.")

    assert calls["n"] == 2
    db.expire_all()
    archived = db.get(Memory, mumbai)
    assert archived.state == "archived" and not archived.is_contradicted and archived.contradicted_by_id is None
    assert result["memory"].state == "active"


def test_concurrent_statements_with_a_far_conflict_leave_one_current_residence():
    for _ in range(3):
        reset_database()
        session = SessionLocal()
        try:
            mumbai = seed(session, "I live in Mumbai.", LIVES_IN_PUNE, "I live in Pune.")
        finally:
            session.close()

        barrier = threading.Barrier(2)
        errors = []

        def worker(statement):
            s = SessionLocal()
            try:
                pipeline = MemoryPipeline(s)
                barrier.wait()
                pipeline.process(statement, "profile")
            except Exception as exc:
                errors.append(exc)
            finally:
                s.close()

        threads = [threading.Thread(target=worker, args=(st,)) for st in ("I live in Pune.", "I live in Delhi.")]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=120)
        assert not errors, errors

        session = SessionLocal()
        try:
            live = live_user_residences(session)
            assert len(live) == 1, live
            losers = session.query(Memory).filter(Memory.is_contradicted.is_(True)).all()
            assert mumbai in [m.id for m in losers]
            assert all(m.state == "archived" and m.contradicted_by_id != m.id for m in losers)
            assert check(session)["consistent"]
        finally:
            session.close()
