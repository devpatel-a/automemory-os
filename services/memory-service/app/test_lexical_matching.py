"""
Lexical retrieval matches whole words (with light plural folding), never
substrings, and uses the full-text GIN index.
"""

from sqlalchemy import text

from app.context.entity_matcher import entity_match_score
from app.context.temporal_matcher import temporal_match_score
from app.database import SessionLocal
from app.lexical import fts_match_any, lexical_score, query_terms
from app.models import Memory
from app.ranking_service import calculate_keyword_score, infer_query_category
from app.retrieval_service import retrieve_memories
from app.testing_support import reset_database
from app.understanding.models import Entity


def test_whole_word_scoring():
    assert lexical_score("I drive a car.", "car") == 1.0
    assert lexical_score("I own two cars.", "car") == 1.0
    for unrelated in ("I love my career.", "That film was scary.", "I joined a carpool."):
        assert lexical_score(unrelated, "car") == 0.0
    assert calculate_keyword_score("My career matters.", "car") == 0.0


def test_multi_term_scoring_keeps_weak_single_overlap():
    assert lexical_score("I live in Pune.", "live Pune") == 1.0
    assert 0 < lexical_score("I live in Mumbai.", "live Pune") < 0.2


def test_query_terms_drop_stop_words():
    assert query_terms("Where do I live?") == ["live"]


def test_context_matchers_are_word_bounded():
    assert entity_match_score([Entity(text="car", label="CONCEPT")], "My career is great.") == 0.0
    assert entity_match_score([Entity(text="car", label="CONCEPT")], "My car is great.") > 0.0
    assert temporal_match_score("What happened last week?", "Lastly, I rested.") == 0.0
    assert infer_query_category("Is it likely to rain?") is None
    assert infer_query_category("What do I like?") == "preference"


def test_sql_lexical_candidates_avoid_substring_false_positives():
    reset_database()
    db = SessionLocal()
    try:
        contents = ["I drive a car.", "I own two cars.", "I love my career.",
                    "That film was scary.", "I joined a carpool."]
        db.add_all([Memory(content=c, category="fact", state="active") for c in contents])
        db.commit()
        hits = {m.content for m in db.query(Memory).filter(fts_match_any(Memory.content, ["car"]))}
        assert hits == {"I drive a car.", "I own two cars."}

        retrieved = [m.content for m, _ in retrieve_memories(db, "car", limit=10)]
        assert set(retrieved[:2]) == hits
    finally:
        db.close()


def test_full_text_predicate_uses_the_gin_index():
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL enable_seqscan = off"))
        query = db.query(Memory.id).filter(fts_match_any(Memory.content, ["car"]))
        compiled = query.statement.compile(db.bind, compile_kwargs={"literal_binds": True})
        plan = "\n".join(r[0] for r in db.execute(text(f"EXPLAIN {compiled}")))
        assert "ix_memories_content_fts" in plan
    finally:
        db.rollback()
        db.close()
