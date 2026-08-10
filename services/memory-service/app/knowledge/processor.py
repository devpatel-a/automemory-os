from app.understanding.models import ParsedMemory

from app.knowledge.fact_extractor import (
    extract_fact,
)

from app.knowledge.classifier import (
    classify_knowledge,
)

from app.knowledge.result_models import (
    KnowledgeResult,
)


def process_knowledge(
    parsed_memory: ParsedMemory,
    candidate_memories: list,
) -> KnowledgeResult:
    """
    Main entry point of the Knowledge Engine.

    Responsibilities:
    - Extract a structured knowledge fact
    - Classify how the new knowledge relates to existing knowledge
    - Return a standardized KnowledgeResult

    This function does NOT:
    - Modify the database
    - Create relationships
    - Update confidence
    - Detect contradictions (future versions)
    """

    fact = extract_fact(parsed_memory)

    decision = classify_knowledge(
        parsed_memory=parsed_memory,
        candidates=candidate_memories,
    )

    return KnowledgeResult(
        fact=fact,
        decision=decision,
    )