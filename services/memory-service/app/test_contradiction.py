from app.models import Memory
from app.understanding.memory_parser import parse_memory
from app.knowledge.contradiction_detector import detect_contradiction
from app.contradiction_service import check_contradiction


def test_contradiction_detection():
    existing = Memory(content="I live in Mumbai.")
    new = parse_memory("I live in Pune.")
    assert detect_contradiction(new, existing) is True

    result = check_contradiction("I live in Pune.", [(existing, 0.1)])
    assert result == existing