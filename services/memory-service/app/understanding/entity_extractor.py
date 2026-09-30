from app.nlp import parse_text
from app.understanding.models import Entity

from app.understanding.memory_entity_extractor import (
    extract_memory_entities,
)



def extract_entities(
    text: str,
) -> list[Entity]:
    """
    Extract named entities using spaCy.
    """

    doc = parse_text(text)

    entities = []

    for ent in doc.ents:

        entities.append(
            Entity(
                text=ent.text,
                label=ent.label_,
            )
        )

    return entities