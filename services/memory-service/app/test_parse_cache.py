"""
Repeated structured extraction must not re-run spaCy: the parse of a given
text is computed once per process (measured: a context build over 8
memories took ~480 ms without the cache and ~25 ms with it).
"""

from app.context.context_engine import ContextEngine
from app.database import SessionLocal
from app.nlp import parse_text
from app.pipeline.memory_pipeline import MemoryPipeline
from app.testing_support import reset_database


def test_repeated_context_builds_do_not_reparse():
    reset_database()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        for statement in ["I live in Mumbai.", "I moved to Pune.", "I like coffee.", "I work at BMW."]:
            pipeline.process(statement, "profile")

        engine = ContextEngine()
        engine.build_context(db, "Where do I live?")  # warm
        misses_before = parse_text.cache_info().misses
        engine.build_context(db, "Where do I live?")
        engine.build_context(db, "Where do I live?")
        assert parse_text.cache_info().misses == misses_before
    finally:
        db.close()


def test_parse_cache_is_bounded():
    assert parse_text.cache_info().maxsize is not None
