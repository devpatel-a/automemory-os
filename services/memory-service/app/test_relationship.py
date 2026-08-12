from app.database import SessionLocal
from app.relationship_service import create_relationship
from app.intelligence.relationship_types import RelationshipType


def test_create_relationship():
    db = SessionLocal()
    try:
        relationship = create_relationship(
            db,
            source_id=1,
            target_id=5,
            relationship_type=RelationshipType.RELATED.value,
        )
        assert relationship.source_memory_id == 1
        assert relationship.target_memory_id == 5
    finally:
        db.close()