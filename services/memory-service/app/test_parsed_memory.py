from app.understanding.memory_parser import parse_memory


def test_parsed_memory_structure():
    memory = parse_memory("I drive my Tesla Model Y to Pune every Monday morning.")
    assert hasattr(memory, "intent")
    assert hasattr(memory, "entities")
    assert hasattr(memory, "temporal")