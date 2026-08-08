from app.understanding.entity_extractor import (
    extract_entities,
)

from app.understanding.intent_detector import (
    detect_intent,
)

from app.understanding.temporal_parser import (
    extract_temporal_information,
)

from app.understanding.models import (
    ParsedMemory,
    Entity,
    TemporalInfo,
)


def parse_memory(text: str) -> ParsedMemory:

    entities = [
        Entity(**entity)
        for entity in extract_entities(text)
    ]

    temporal = [
        TemporalInfo(**item)
        for item in extract_temporal_information(text)
    ]

    return ParsedMemory(
        content=text,
        intent=detect_intent(text).value,
        entities=entities,
        temporal=temporal,
    )