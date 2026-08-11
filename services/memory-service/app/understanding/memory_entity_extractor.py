from app.understanding.models import Entity

MEMORY_KEYWORDS = {
    "coffee": "drink",
    "tea": "drink",
    "python": "technology",
    "fastapi": "technology",
    "postgresql": "technology",
    "tesla": "vehicle",
    "dark mode": "preference",
    "linux": "technology",
    "macbook": "device",
    "gym": "activity",
    "football": "sport",
}


def extract_memory_entities(text: str) -> list[Entity]:
    """
    Extract memory-specific concepts.
    """

    entities = []

    lower = text.lower()

    for keyword, label in MEMORY_KEYWORDS.items():

        if keyword in lower:

            entities.append(
                Entity(
                    text=keyword,
                    label=label,
                )
            )

    return entities