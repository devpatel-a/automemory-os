from app.intelligence.decision_engine import decide
from app.intelligence.decision_types import MemoryDecision


def test_decision_engine_candidates():
    tests = [
        ([], MemoryDecision.NEW),
        ([(None, 0.03)], MemoryDecision.IGNORE),
        ([(None, 0.15)], MemoryDecision.REINFORCE),
        ([(None, 0.35)], MemoryDecision.RELATED),
        ([(None, 0.80)], MemoryDecision.NEW),
    ]
    for candidates, expected in tests:
        result = decide(candidates)
        assert result == expected