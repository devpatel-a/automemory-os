from app.understanding.memory_entity_extractor import extract_memory_entities


def test_memory_entity_extractor():
    entities = extract_memory_entities("I like coffee and Python on my MacBook.")
    texts = [e.text for e in entities]
    assert "coffee" in texts
    assert "python" in texts
    assert "macbook" in texts