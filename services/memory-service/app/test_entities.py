from app.understanding.entity_extractor import extract_entities


def test_entities_extraction():
    text = "Apple CEO Tim Cook visited New York on Monday."
    entities = extract_entities(text)
    assert len(entities) > 0
    labels = [e.label for e in entities]
    assert any(l in ["ORG", "PERSON", "GPE", "DATE"] for l in labels)