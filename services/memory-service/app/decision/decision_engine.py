from app.decision.action_models import DecisionResult
from app.decision.decision_types import MemoryAction
from app.knowledge.knowledge_types import KnowledgeDecision


def decide(
    knowledge_result,
) -> DecisionResult:
    """
    Decide what AutoMemory OS should do with the incoming memory.
    """

    decision = knowledge_result.decision

    if decision == KnowledgeDecision.NEW:
        return DecisionResult(
            action=MemoryAction.STORE,
            reason="New knowledge detected.",
        )

    if decision == KnowledgeDecision.REINFORCEMENT:
        return DecisionResult(
            action=MemoryAction.REINFORCE,
            reason="Existing memory reinforced.",
        )

    if decision == KnowledgeDecision.RELATED:
        return DecisionResult(
            action=MemoryAction.STORE,
            reason="Related memory stored separately.",
        )

    if decision in (KnowledgeDecision.UPDATE, KnowledgeDecision.SUPERSESSION):
        return DecisionResult(
            action=MemoryAction.UPDATE,
            reason="Fact supersession or update.",
        )

    if decision == KnowledgeDecision.MERGE:
        return DecisionResult(
            action=MemoryAction.MERGE,
            reason="Equivalent memories merged into canonical memory.",
        )

    if decision == KnowledgeDecision.CONTRADICTION:
        return DecisionResult(
            action=MemoryAction.ARCHIVE,
            reason="Contradiction detected.",
        )

    return DecisionResult(
        action=MemoryAction.STORE,
        reason="Default action.",
    )