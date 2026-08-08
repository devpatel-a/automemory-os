from app.models_relationship import MemoryRelationship


def create_relationship(
    db,
    source_id,
    target_id,
    relationship_type,
):

    relationship = MemoryRelationship(
        source_memory_id=source_id,
        target_memory_id=target_id,
        relationship_type=relationship_type,
    )

    db.add(relationship)

    return relationship

def get_related_memories(
    db,
    memory_id,
):
    return (
        db.query(MemoryRelationship)
        .filter(
            MemoryRelationship.source_memory_id == memory_id
        )
        .all()
    )