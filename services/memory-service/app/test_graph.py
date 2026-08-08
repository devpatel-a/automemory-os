from app.database import SessionLocal
from app.relationship_service import (
    get_related_memories,
)

db = SessionLocal()

relationships = get_related_memories(
    db,
    1,
)

for relation in relationships:

    print(
        relation.relationship_type,
        "->",
        relation.target_memory_id,
    )