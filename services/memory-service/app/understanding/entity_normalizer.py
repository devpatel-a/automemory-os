from app.understanding.models import Entity


def normalize_entities(
    entities: list[Entity],
) -> list[Entity]:
    """
    Remove duplicate entities while preserving order.
    """

    seen = set()

    normalized = []

    for entity in entities:

        key = (
            entity.text.lower(),
            entity.label.lower(),
        )

        if key not in seen:

            seen.add(key)

            normalized.append(entity)

    return normalized