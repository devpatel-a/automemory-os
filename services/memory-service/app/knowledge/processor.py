from app.understanding.models import ParsedMemory
from app.knowledge.classifier import assess_knowledge
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.knowledge.result_models import KnowledgeResult


def get_memory_object(item):
    if hasattr(item, "content"):
        return item
    if hasattr(item, "__getitem__"):
        return item[0]
    return item


def process_knowledge(
    parsed_memory: ParsedMemory,
    candidate_memories: list,
    historical_ids=frozenset(),
) -> KnowledgeResult:
    """
    Main entry point of the Knowledge Engine.

    Responsibilities:
    - Extract a structured knowledge fact
    - Classify how new knowledge relates to existing knowledge (UPDATE, MERGE, REINFORCEMENT, CONTRADICTION, SUPERSESSION, RELATED, NEW)
    - Identify the exact target memory and deterministic reason codes
    - Return a standardized KnowledgeResult
    """
    result = assess_knowledge(
        parsed_memory=parsed_memory,
        candidates=candidate_memories,
        historical_ids=historical_ids,
    )

    # Contradiction safety net for decisions that are not already evolution decisions
    if (
        result.decision
        not in (
            KnowledgeDecision.UPDATE,
            KnowledgeDecision.SUPERSESSION,
            KnowledgeDecision.MERGE,
            KnowledgeDecision.REINFORCEMENT,
            KnowledgeDecision.CONTRADICTION,
        )
        and candidate_memories
    ):
        for candidate in candidate_memories:
            existing_mem = get_memory_object(candidate)
            if getattr(existing_mem, "id", None) in historical_ids:
                continue
            if detect_contradiction(parsed_memory, existing_mem):
                return KnowledgeResult(
                    fact=result.fact,
                    decision=KnowledgeDecision.CONTRADICTION,
                    target_memory_id=getattr(existing_mem, "id", None),
                    reason_codes=["contradiction_detector", "conflicting_current_claims"],
                )

    return result
