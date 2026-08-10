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