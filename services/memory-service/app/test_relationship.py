from app.database import SessionLocal
from app.relationship_service import create_relationship
from app.intelligence.relationship_types import (
    RelationshipType,
)

db = SessionLocal()

relationship = create_relationship(
    db,
    source_id=1,
    target_id=5,
    relationship_type=RelationshipType.RELATED.value,
)

db.commit()

print("Relationship created!")