from app.database import SessionLocal
from app.context.context_engine import ContextEngine


def test_context_engine_building():
    db = SessionLocal()
    try:
        engine = ContextEngine()
        context = engine.build_context(db=db, query="Recommend a cafe")
        assert context is not None
        assert context.query == "Recommend a cafe"
    finally:
        db.close()