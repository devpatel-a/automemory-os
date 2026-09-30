from pydantic import BaseModel

from app.knowledge.fact_models import (
    KnowledgeFact,
)

from app.knowledge.knowledge_types import (
    KnowledgeDecision,
)


class KnowledgeResult(BaseModel):

    fact: KnowledgeFact | None

    decision: KnowledgeDecision

    # The exact existing memory the decision acts on (supersession/contradiction
    # target, reinforcement target, ...), as reasoned about by the classifier.
    target_memory_id: int | None = None

    # Concise, deterministic, machine-readable reasons (never free text).
    reason_codes: list[str] = []