from app.knowledge.fact_models import (
    KnowledgeFact,
)


MAX_CONFIDENCE = 1.0
MIN_CONFIDENCE = 0.0


def reinforce_fact(
    fact: KnowledgeFact,
):

    fact.evidence_count += 1

    fact.confidence = min(
        MAX_CONFIDENCE,
        fact.confidence + 0.10,
    )

    return fact


def contradict_fact(
    fact: KnowledgeFact,
):

    fact.contradiction_count += 1

    fact.confidence = max(
        MIN_CONFIDENCE,
        fact.confidence - 0.20,
    )

    return fact