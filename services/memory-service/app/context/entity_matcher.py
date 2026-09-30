from app.knowledge.temporal_cues import contains_cue
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

    matches = 0

    for entity in query_entities:

        # Whole-word/phrase match: entity "car" must not match "career".
        if entity.text.strip() and contains_cue(memory_content, [entity.text.lower()]):
            matches += 1

    return matches * ENTITY_MATCH_WEIGHT