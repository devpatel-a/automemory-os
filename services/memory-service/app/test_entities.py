from app.understanding.entity_extractor import extract_entities

text = "Apple CEO Tim Cook visited New York on Monday."

print("Input:")
print(text)

entities = extract_entities(text)

print("\nEntities:")
print(entities)

print("\nLength:", len(entities))