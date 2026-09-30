import re

from app.understanding.models import Entity

_LEADING_DETERMINERS = {
    "a", "an", "the", "my", "our", "your", "his", "her", "their", "its",
    "this", "that", "these", "those", "every", "each", "some", "any",
}
_EDGE_PUNCTUATION = ".,!?;:\"'()[]{}"


def normalize_entity_name(text: str) -> str:
    """
    Canonical, conservative entity key: lower-case, whitespace collapsed,
    surrounding punctuation and leading determiners/possessives removed.

    "My MacBook Air" -> "macbook air"; "Rahul Patel" -> "rahul patel".
    Names are never shortened further: "rahul patel" != "rahul".
    """
    tokens = re.sub(r"\s+", " ", (text or "").strip()).split(" ")
    tokens = [t.strip(_EDGE_PUNCTUATION).lower() for t in tokens]
    tokens = [t for t in tokens if t]
    while tokens and tokens[0] in _LEADING_DETERMINERS:
        tokens.pop(0)
    if tokens and tokens[-1].endswith("'s"):
        tokens[-1] = tokens[-1][:-2]
    return " ".join(tokens)


def normalize_entities(
    entities: list[Entity],
) -> list[Entity]:
    """
    Remove duplicate entities while preserving insertion order.

    Entities are keyed by their normalized name only: a generic CONCEPT
    entity that names the same thing as an earlier NER entity (e.g. "Pune"
    GPE and "pune" CONCEPT) is dropped instead of becoming a second node.
    """

    normalized = []

    seen = set()

    for entity in entities:

        key = normalize_entity_name(entity.text)

        if not key or key in seen:
            continue

        seen.add(key)

        normalized.append(entity)

    return normalized
