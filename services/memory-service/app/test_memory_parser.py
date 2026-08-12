from app.understanding.memory_parser import parse_memory


def test_memory_parser():
    memory = parse_memory("I drive my Tesla Model Y to Pune every Monday morning.")
    assert memory.content == "I drive my Tesla Model Y to Pune every Monday morning."
    assert len(memory.entities) > 0
    assert len(memory.temporal) > 0