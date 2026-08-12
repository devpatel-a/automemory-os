from app.knowledge.fact_models import KnowledgeFact
from app.knowledge.confidence_engine import reinforce_fact, contradict_fact


def test_confidence_engine():
    fact = KnowledgeFact(
        entity="user",
        attribute="favorite_drink",
        value="coffee",
    )
    assert fact.confidence == 0.60
    assert fact.evidence_count == 1

    reinforce_fact(fact)
    assert round(fact.confidence, 2) == 0.70
    assert fact.evidence_count == 2

    contradict_fact(fact)
    assert round(fact.confidence, 2) == 0.50
    assert fact.contradiction_count == 1