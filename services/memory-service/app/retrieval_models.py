"""
Structured retrieval candidate.

Each signal is measured independently and kept separately, so ranking is
explainable ("why was this memory retrieved?") and no single field (such as
the legacy ContextCandidate.similarity) is overloaded with several meanings.
Signals are None when a stage did not measure them.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models import Memory


class RetrievalCandidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory: Memory
    memory_id: int

    # Retrieval-stage signals (app/retrieval_service.py)
    semantic_score: float | None = None      # 1 - cosine distance
    lexical_score: float = 0.0               # whole-word lexical overlap
    graph_score: float = 0.0                 # linked to an entity resolved from the query
    importance: float = 0.0
    recency: float = 0.0
    access_frequency: float = 0.0
    category_score: float = 0.0
    retrieval_score: float = 0.0             # weighted hybrid score

    # Context-stage signals (app/context/*)
    entity_score: float | None = None        # query entities named in the memory
    attribute_score: float | None = None     # structured fact entity/attribute match
    temporal_score: float | None = None      # temporal cue + temporal-intent alignment
    relationship_score: float | None = None  # not measured yet (reserved)

    # State
    confidence: float | None = None
    lifecycle_state: str | None = None
    temporal_state: str | None = None

    final_score: float = 0.0
    reasons: list[str] = Field(default_factory=list)

    def signals(self) -> dict[str, float | None]:
        return {
            "semantic": self.semantic_score,
            "lexical": self.lexical_score,
            "graph": self.graph_score,
            "importance": self.importance,
            "recency": self.recency,
            "access_frequency": self.access_frequency,
            "category": self.category_score,
            "retrieval": self.retrieval_score,
            "entity": self.entity_score,
            "attribute": self.attribute_score,
            "temporal": self.temporal_score,
            "relationship": self.relationship_score,
            "final": self.final_score,
        }
