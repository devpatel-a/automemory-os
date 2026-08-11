from app.understanding.models import Entity


ENTITY_MATCH_WEIGHT = 0.10


def entity_match_score(
    query_entities: list[Entity],
    memory_content: str,
) -> float:
    """
    Compute a score bonus based on
    explicit entity matches.
    """

    if not query_entities:
        return 0.0

    content = memory_content.lower()

    matches = 0

    for entity in query_entities:

        if entity.text.lower() in content:
            matches += 1

    return matches * ENTITY_MATCH_WEIGHT