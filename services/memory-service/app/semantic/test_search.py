from app.database import SessionLocal
from app.semantic.semantic_service import semantic_search


def test_semantic_search():
    db = SessionLocal()
    try:
        results = semantic_search(
            db,
            "I like beverages",
        )
        assert isinstance(results, list)
        for memory, distance in results:
            assert hasattr(memory, "content")
            assert isinstance(distance, (float, type(None)))
    finally:
        db.close()