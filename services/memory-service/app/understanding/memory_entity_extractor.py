from app.understanding.models import Entity

MEMORY_KEYWORDS = {

    # ---------------- Drinks ----------------

    "coffee": "drink",
    "tea": "drink",
    "cappuccino": "drink",
    "espresso": "drink",
    "latte": "drink",
    "americano": "drink",
    "mocha": "drink",
    "macchiato": "drink",

    # ---------------- Places ----------------

    "cafe": "place",
    "café": "place",
    "starbucks": "place",
    "restaurant": "place",
    "office": "place",
    "home": "place",
    "school": "place",
    "college": "place",

    # ---------------- Technology ----------------

    "python": "technology",
    "fastapi": "technology",
    "postgresql": "technology",
    "docker": "technology",
    "kubernetes": "technology",
    "langgraph": "technology",
    "langchain": "technology",
    "rag": "technology",
    "llm": "technology",

    # ---------------- Vehicles ----------------

    "tesla": "vehicle",
    "car": "vehicle",
    "bike": "vehicle",

    # ---------------- Preferences ----------------

    "dark mode": "preference",
    "light mode": "preference",

    # ---------------- Devices ----------------

    "macbook": "device",
    "iphone": "device",
    "ipad": "device",
    "laptop": "device",

    # ---------------- Activities ----------------

    "gym": "activity",
    "running": "activity",
    "reading": "activity",
    "coding": "activity",

    # ---------------- Sports ----------------

    "football": "sport",
    "cricket": "sport",
    "tennis": "sport",
}


def extract_memory_entities(
    text: str,
) -> list[Entity]:
    """
    Extract memory-specific entities
    using keyword matching.
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