from app.understanding.models import Entity


def normalize_entities(
    entities: list[Entity],
) -> list[Entity]:
    """
    Remove duplicate entities while
    preserving insertion order.
    """

    normalized = []

    seen = set()

    for entity in entities:

        key = (

            entity.text.lower(),

            entity.label.lower(),

        )

        if key in seen:
            continue

        seen.add(key)

        normalized.append(entity)

    return normalized