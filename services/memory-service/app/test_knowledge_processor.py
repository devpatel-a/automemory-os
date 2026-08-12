from app.understanding.memory_parser import parse_memory
from app.knowledge.processor import process_knowledge


def test_knowledge_processor():
    parsed = parse_memory("My favorite drink is coffee.")
    result = process_knowledge(parsed, [])
    assert result is not None
    assert result.fact is not None
    assert result.fact.attribute == "favorite_drink"