from app.understanding.entity_extractor import (
    extract_entities,
)

from app.understanding.entity_normalizer import (
    normalize_entities,
)

from app.understanding.memory_entity_extractor import (
    extract_memory_entities,
)

from app.understanding.intent_detector import (
    detect_intent,
)

from app.understanding.temporal_parser import (
    extract_temporal_information,
)

from app.understanding.models import (
    ParsedMemory,
    TemporalInfo,
)


def parse_memory(text: str) -> ParsedMemory:
    """
    Parse a raw user memory into a structured representation.

    Pipeline:
    1. Extract named entities using spaCy.
    2. Extract memory-specific entities (coffee, Python, Tesla, etc.).
    3. Merge both entity lists.
    4. Detect user intent.
    5. Extract temporal information.
    6. Return a ParsedMemory object.
    """

    # Named entities from spaCy
    spacy_entities = extract_entities(text)

    # Memory-specific entities
    memory_entities = extract_memory_entities(text)

    # Merge entities
    entities = normalize_entities(
        spacy_entities + memory_entities
    )

    # Temporal information
    temporal = [
        TemporalInfo(**item)
        for item in extract_temporal_information(text)
    ]

    # Return parsed memory
    return ParsedMemory(
        content=text,
        intent=detect_intent(text).value,
        entities=entities,
        temporal=temporal,
    )