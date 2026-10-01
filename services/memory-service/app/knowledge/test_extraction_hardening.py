"""
Extraction hardening (Section 1): regression tests for extractor defects that
would make knowledge_facts rows wrong, plus the nearby valid inputs that must
keep their behavior.

- A possessed non-relation subject ("My parents live near Pune") is the
  possessed noun, not the user.
- A value or subject that only refers to something stated elsewhere
  ("I live there", "I like them", "We live in Pune", "Thank you") is flagged
  is_placeholder; a question ("Do I live in Pune?") is flagged is_question and
  produces no index row.
"""

import pytest
from sqlalchemy import text

from app.context.query_intent import analyze_query
from app.database import SessionLocal
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.fact_index import check, derive_fact_row, lookup_fact_rows, reindex
from app.knowledge.fact_index_model import KnowledgeFactRow
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.provenance.models import EXTRACTOR_VERSION
from app.testing_support import reset_database
from app.understanding.memory_parser import parse_memory


def fact(statement):
    return extract_fact(parse_memory(statement))


def triple(statement):
    f = fact(statement)
    return (f.entity, f.attribute, f.value)


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ------------------------------------------------- possessed-subject entity

@pytest.mark.parametrize("statement, expected", [
    ("My parents live near Pune.", ("parents", "residence", "Pune")),
    ("My parents live in Pune.", ("parents", "residence", "Pune")),
    ("My kids study in Pune.", ("kids", "learning_topic", "Pune")),
    ("My team works at Google.", ("team", "employer", "Google")),
    ("My laptop runs Linux.", ("laptop", "run", "Linux")),
])
def test_possessed_subject_is_the_entity_not_the_user(statement, expected):
    assert triple(statement) == expected
    assert fact(statement).is_placeholder is False


@pytest.mark.parametrize("statement, expected", [
    # relation nouns and named people keep their entity
    ("My sister lives in Pune.", ("sister", "residence", "Pune")),
    ("My brother works at Infosys.", ("brother", "employer", "Infosys")),
    ("My friend Rahul lives in Delhi.", ("Rahul", "residence", "Delhi")),
    # copular "my X is Y" describes the user
    ("My name is Dev Patel.", ("user", "name", "Dev Patel")),
    ("My favorite drink is coffee.", ("user", "favorite_drink", "coffee")),
    # "my" on the object of a user subject: still the user
    ("I love my dog.", ("user", "preference", "dog")),
    ("I use my MacBook Air for development.", ("user", "device", "MacBook Air")),
    ("I live in Pune.", ("user", "residence", "Pune")),
])
def test_nearby_possessive_and_user_facts_are_unchanged(statement, expected):
    assert triple(statement) == expected
    assert fact(statement).is_placeholder is False


def test_relationship_to_user_is_kept_for_relation_nouns():
    assert fact("My sister lives in Pune.").relationship_to_user == "sister"
    assert fact("My friend Rahul lives in Delhi.").relationship_to_user == "friend"


# ------------------------------------------------------------ placeholders

@pytest.mark.parametrize("statement, value", [
    ("I live there.", "unknown"),       # deictic adverb: no value
    ("I live here.", "unknown"),
    ("I moved there.", "unknown"),
    ("I work there.", "unknown"),
    ("I live near there.", "unknown"),
    ("I like it.", "it"),               # PLACEHOLDER_VALUES
    ("I like them.", "them"),           # pronoun value
    ("I like those.", "those"),
    ("Thank you so much.", "you"),      # conversational, pronoun value
])
def test_placeholder_values_are_flagged(statement, value):
    f = fact(statement)
    assert f.value == value
    assert f.is_placeholder is True
    assert f.is_question is False


@pytest.mark.parametrize("statement", [
    "We live in Pune.",
    "He lives in Pune.",
    "They work at Google.",
    "That sounds good to me.",
])
def test_pronoun_subjects_are_flagged(statement):
    assert fact(statement).is_placeholder is True


@pytest.mark.parametrize("statement, value", [
    ("I live in Pune.", "Pune"),
    ("I live in Washington.", "Washington"),   # contains no deictic token
    ("I visited Hereford.", "Hereford"),       # "here" inside a real name
    ("I like Python.", "Python"),
    ("I like Thai food.", "Thai food"),
    ("I work at Google.", "Google"),
    ("Rahul lives in Delhi.", "Delhi"),
])
def test_real_values_are_not_placeholders(statement, value):
    f = fact(statement)
    assert f.value == value
    assert f.is_placeholder is False


def test_placeholder_flag_does_not_change_value_or_confidence():
    # The flag is additive: evolution reads value/confidence, not the flag.
    f = fact("I like them.")
    assert (f.entity, f.attribute, f.value, f.confidence) == ("user", "preference", "them", 0.85)
    assert fact("I live there.").confidence == 0.35


# --------------------------------------------------------------- questions

@pytest.mark.parametrize("statement", [
    "Do I live in Pune?",
    "Where do I live?",
    "Can you remind me later?",
])
def test_questions_are_flagged(statement):
    assert fact(statement).is_question is True


def test_statements_are_not_questions():
    for statement in ("I live in Pune.", "I live in Pune", "My parents live near Pune!"):
        assert fact(statement).is_question is False


def test_query_analysis_still_reads_question_facts():
    # Queries are questions: query intent must still get entity/attribute.
    assert (analyze_query("Where do I live?").entity, analyze_query("Where do I live?").attribute) == (
        "user", "residence",
    )
    intent = analyze_query("Where do my parents live?")
    assert (intent.entity, intent.attribute) == ("parents", "residence")


def test_no_fact_inputs_still_produce_nothing():
    assert fact("Wow.") is None
    assert derive_fact_row("Thanks!") is None


# -------------------------------------------------- knowledge_facts rows

@pytest.mark.parametrize("statement", ["Do I live in Pune?", "Where do I live?", "Can you remind me later?"])
def test_questions_produce_no_index_row(statement):
    assert derive_fact_row(statement) is None


@pytest.mark.parametrize("statement", [
    "I live there.", "I like them.", "We live in Pune.", "He lives in Pune.",
    "Thank you so much.", "That sounds good to me.",
])
def test_placeholder_rows_are_flagged(statement):
    assert derive_fact_row(statement)["is_placeholder"] is True


@pytest.mark.parametrize("statement, keys", [
    ("My parents live near Pune.", ("parents", "residence", "pune")),
    ("I live in Pune.", ("user", "residence", "pune")),
    ("I visited Hereford.", ("user", "visit", "hereford")),
])
def test_real_rows_are_not_placeholders(statement, keys):
    row = derive_fact_row(statement)
    assert (row["entity_key"], row["attribute_key"], row["value_key"]) == keys
    assert row["is_placeholder"] is False


def test_parents_fact_is_not_indexed_as_user_residence(db):
    pipeline = MemoryPipeline(db)
    user = pipeline.process("I live in Pune.", "profile")["memory"].id
    parents = pipeline.process("My parents live near Pune.", "profile")["memory"].id
    db.expire_all()

    assert [r.memory_id for r in lookup_fact_rows(db, "user", "residence")] == [user]
    assert [r.memory_id for r in lookup_fact_rows(db, "parents", "residence")] == [parents]
    assert check(db)["consistent"]


def test_question_memory_has_no_row_and_index_stays_consistent(db):
    # Stored alone so no evolution decision (out of scope here) interferes.
    question = MemoryPipeline(db).process("Do I live in Pune?", "profile")["memory"].id
    db.expire_all()
    assert db.get(KnowledgeFactRow, question) is None
    assert check(db)["consistent"]


def test_parents_statement_no_longer_merges_into_user_residence(db):
    # Before the fix both extracted as (user, residence, Pune) and the second
    # was merged into the first, rewriting the user's memory text.
    pipeline = MemoryPipeline(db)
    user = pipeline.process("I live in Pune.", "profile")["memory"].id
    parents = pipeline.process("My parents live in Pune.", "profile")["memory"].id
    db.expire_all()

    assert parents != user
    assert [(m.id, m.content, m.state) for m in db.query(Memory).order_by(Memory.id)] == [
        (user, "I live in Pune.", "active"),
        (parents, "My parents live in Pune.", "active"),
    ]


def test_rows_from_previous_extractor_are_stale_and_reindex_refreshes_them(db):
    (memory_id,) = (
        MemoryPipeline(db).process("My parents live near Pune.", "profile")["memory"].id,
    )
    # simulate a row written by the previous extractor (entity collapsed to user)
    db.execute(
        text("UPDATE knowledge_facts SET entity_key = 'user', extractor_version = 'deterministic-nlp-0.10' "
             "WHERE memory_id = :i"),
        {"i": memory_id},
    )
    db.commit()
    assert check(db)["stale"] == [memory_id]

    reindex(SessionLocal)
    db.expire_all()
    row = db.get(KnowledgeFactRow, memory_id)
    assert (row.entity_key, row.extractor_version) == ("parents", EXTRACTOR_VERSION)
    assert check(db)["consistent"]
