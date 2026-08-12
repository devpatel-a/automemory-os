from app.database import SessionLocal
from app.retrieval_service import retrieve_memories


def test_retrieval_memories():
    db = SessionLocal()
    try:
        results = retrieve_memories(db, "I like beverages")
        assert isinstance(results, list)
    finally:
        db.close()