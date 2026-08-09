from app.knowledge.knowledge_types import (
    KnowledgeDecision,
)


def classify_knowledge(
    parsed_memory,
    candidates,
):

    if not candidates:

        return KnowledgeDecision.NEW

    best_match, distance = candidates[0]

    if distance is None:

        return KnowledgeDecision.NEW

    if distance < 0.10:

        return KnowledgeDecision.REINFORCEMENT

    if distance < 0.35:

        return KnowledgeDecision.RELATED

    return KnowledgeDecision.NEW