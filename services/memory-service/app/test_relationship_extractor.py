from app.intelligence.decision_types import MemoryDecision
from app.intelligence.relationship_extractor import extract_relationship


def test_relationship_extractor():
    for decision in MemoryDecision:
        rel = extract_relationship(decision)
        if decision.value in ["reinforce", "related", "ignore"]:
            assert rel is not None
        else:
            assert rel is None