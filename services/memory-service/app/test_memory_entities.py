from app.understanding.memory_entity_extractor import (
    extract_memory_entities,
)

entities = extract_memory_entities(
    "I like coffee and Python on my MacBook."
)

for entity in entities:
    print(entity)