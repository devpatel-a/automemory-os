from app.understanding.memory_parser import parse_memory
from app.knowledge.fact_extractor import extract_fact


def test_fact_extractor():
    parsed1 = parse_memory("I live in Pune.")
    fact1 = extract_fact(parsed1)
    assert fact1 is not None
    assert fact1.attribute == "residence"
    assert fact1.value == "pune"

    parsed2 = parse_memory("My favorite drink is coffee.")
    fact2 = extract_fact(parsed2)
    assert fact2 is not None
    assert fact2.attribute == "favorite_drink"
    assert fact2.value == "coffee"