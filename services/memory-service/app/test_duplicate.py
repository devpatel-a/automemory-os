from app.database import SessionLocal
from app.semantic.semantic_service import semantic_search
from app.duplicate_service import find_duplicate


def test_duplicate_service_search():
    db = SessionLocal()
    try:
        results = semantic_search(
            db,
            "Coffee is my favorite beverage",
        )
        duplicate = find_duplicate(results)
        assert duplicate is None or hasattr(duplicate, "content")
    finally:
        db.close()