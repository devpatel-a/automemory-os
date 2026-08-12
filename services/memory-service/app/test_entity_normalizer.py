from app.understanding.models import Entity
from app.understanding.entity_normalizer import normalize_entities


def test_entity_normalizer():
    entities = [
        Entity(text="Python", label="technology"),
        Entity(text="python", label="technology"),
        Entity(text="Pune", label="LOC"),
    ]
    normalized = normalize_entities(entities)
    assert len(normalized) == 2
    assert normalized[0].text == "Python"
    assert normalized[1].text == "Pune"