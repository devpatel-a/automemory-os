from app.understanding.entity_extractor import (
    extract_entities,
)

from app.understanding.memory_entity_extractor import (
    extract_memory_entities,
)

from app.understanding.entity_normalizer import (
    normalize_entities,
)

from app.understanding.models import Entity


def extract_query_entities(
    query: str,
) -> list[Entity]:
    """
    Extract and normalize entities
    from a user query.
    """

    spacy_entities = extract_entities(
        query,
    )

    memory_entities = extract_memory_entities(
        query,
    )

    return normalize_entities(
        spacy_entities + memory_entities,
    )