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


def parse_memory(
    text: str,
) -> ParsedMemory:
    """
    Parse raw text into a structured
    ParsedMemory object.
    """

    # Named entities
    spacy_entities = extract_entities(text)

    # Domain entities
    memory_entities = extract_memory_entities(text)

    # Merge & deduplicate
    entities = normalize_entities(
        spacy_entities + memory_entities
    )

    # Temporal expressions
    temporal = [

        TemporalInfo(**item)

        for item in extract_temporal_information(
            text
        )

    ]

    return ParsedMemory(

        content=text,

        intent=detect_intent(text).value,

        entities=entities,

        temporal=temporal,

    )