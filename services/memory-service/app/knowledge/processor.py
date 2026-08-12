from app.understanding.models import ParsedMemory
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.classifier import classify_knowledge
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.knowledge.result_models import KnowledgeResult


def process_knowledge(
    parsed_memory: ParsedMemory,
    candidate_memories: list,
) -> KnowledgeResult:
    """
    Main entry point of the Knowledge Engine.

    Responsibilities:
    - Extract a structured knowledge fact
    - Classify how the new knowledge relates to existing knowledge
    - Detect contradictions against existing candidate memories
    - Return a standardized KnowledgeResult
    """
    fact = extract_fact(parsed_memory)

    if candidate_memories:
        for candidate in candidate_memories:
            existing_mem = (
                candidate[0]
                if isinstance(candidate, (tuple, list))
                else candidate
            )
            if detect_contradiction(parsed_memory, existing_mem):
                return KnowledgeResult(
                    fact=fact,
                    decision=KnowledgeDecision.CONTRADICTION,
                )

    decision = classify_knowledge(
        parsed_memory=parsed_memory,
        candidates=candidate_memories,
    )

    return KnowledgeResult(
        fact=fact,
        decision=decision,
    )