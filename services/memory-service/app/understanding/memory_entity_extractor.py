"""
Generic (value-agnostic) entity extraction from noun chunks.

Replaces the former hard-coded keyword list (coffee, starbucks, python,
tesla, macbook, cricket, ...). Any noun phrase is a candidate concept entity,
so previously unseen names, products, places, topics or books work the same
way as well-known ones. Named-entity labels come from spaCy NER
(entity_extractor.py); these noun-chunk entities are labelled CONCEPT.
"""

from app.nlp import parse_text
from app.understanding.entity_normalizer import normalize_entity_name
from app.understanding.models import Entity

CONCEPT_LABEL = "CONCEPT"

# Question words and generic placeholders are not entities.
_NON_ENTITY_WORDS = {
    "what", "who", "whom", "which", "where", "when", "why", "how",
    "something", "anything", "everything", "nothing", "thing", "things",
    "someone", "anyone", "everyone", "one",
}


def extract_memory_entities(
    text: str,
) -> list[Entity]:
    """
    Extract concept entities from noun chunks, normalized with
    normalize_entity_name ("my MacBook Air" -> "macbook air").
    """
    entities = []
    seen = set()

    for chunk in parse_text(text).noun_chunks:
        if chunk.root.pos_ == "PRON":
            continue
        content_tokens = [
            t for t in chunk
            if t.pos_ not in ("DET", "PRON") and t.dep_ != "poss"
        ]
        if not content_tokens:
            continue
        name = normalize_entity_name(" ".join(t.text for t in content_tokens))
        if not name or name in _NON_ENTITY_WORDS or name in seen:
            continue
        seen.add(name)
        entities.append(Entity(text=name, label=CONCEPT_LABEL))

    return entities
