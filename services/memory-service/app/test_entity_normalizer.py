from app.understanding.models import Entity

from app.understanding.entity_normalizer import (
    normalize_entities,
)

entities = [

    Entity(
        text="Python",
        label="technology",
    ),

    Entity(
        text="python",
        label="technology",
    ),

    Entity(
        text="Pune",
        label="LOC",
    ),

]

normalized = normalize_entities(
    entities,
)

for entity in normalized:

    print(entity)