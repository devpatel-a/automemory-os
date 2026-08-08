from app.intelligence.relationship_types import (
    RelationshipType,
)


def extract_relationship(
    decision,
):
    """
    Convert a memory decision into
    a graph relationship.
    """

    mapping = {

        "reinforce":
            RelationshipType.SUPPORTS,

        "related":
            RelationshipType.RELATED,

        "ignore":
            RelationshipType.DUPLICATE_OF,
    }

    return mapping.get(decision.value)