from app.understanding.models import ParsedMemory
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.classifier import classify_knowledge
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
) -> KnowledgeResult:
    """
    Main entry point of the Knowledge Engine.

    Responsibilities:
    - Extract a structured knowledge fact
    - Classify how new knowledge relates to existing knowledge (UPDATE, MERGE, REINFORCEMENT, CONTRADICTION, SUPERSESSION, RELATED, NEW)
    - Return a standardized KnowledgeResult
    """
    fact = extract_fact(parsed_memory)

    # 1. Classification (handles UPDATE, MERGE, REINFORCEMENT, SUPERSESSION, RELATED, NEW)
    decision = classify_knowledge(
        parsed_memory=parsed_memory,
        candidates=candidate_memories,
    )

    # 2. Contradiction Check if not already classified as UPDATE, SUPERSESSION, MERGE, or REINFORCEMENT
    if (
        decision
        not in (
            KnowledgeDecision.UPDATE,
            KnowledgeDecision.SUPERSESSION,
            KnowledgeDecision.MERGE,
            KnowledgeDecision.REINFORCEMENT,
        )
        and candidate_memories
    ):
        for candidate in candidate_memories:
            existing_mem = get_memory_object(candidate)
            if detect_contradiction(parsed_memory, existing_mem):
                decision = KnowledgeDecision.CONTRADICTION
                break

    return KnowledgeResult(
        fact=fact,
        decision=decision,
    )