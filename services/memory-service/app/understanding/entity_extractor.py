import spacy

from app.understanding.models import Entity

nlp = spacy.load("en_core_web_sm")


def extract_entities(text: str) -> list[Entity]:
    """
    Extract named entities using spaCy.
    """

    doc = nlp(text)

    entities = []

    for entity in doc.ents:
        entities.append(
            Entity(
                text=entity.text,
                label=entity.label_,
            )
        )

    return entities