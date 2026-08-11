from app.understanding.memory_entity_extractor import (
    extract_memory_entities,
)

from app.understanding.entity_extractor import (
    extract_entities,
)

from app.understanding.entity_normalizer import (
    normalize_entities,
)


def extract_query_entities(
    query: str,
):
    """
    Extract entities from a user query.
    """

    spacy = extract_entities(query)

    memory = extract_memory_entities(query)

    return normalize_entities(
        spacy + memory,
    )