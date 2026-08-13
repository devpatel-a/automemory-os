from pydantic import BaseModel, ConfigDict, Field

from app.models import Memory


class ContextCandidate(BaseModel):
    """
    Represents a retrieved memory together with all evidence scoring
    and conflict resolution information used during context selection.

    Note:
        ContextCandidate.similarity is retained for backward compatibility,
        but in the current ContextEngine pipeline it represents the final
        hybrid retrieval score returned by retrieve_memories().
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    memory: Memory

    similarity: float

    score: float = 0.0

    evidence_score: float = 0.0

    explanation: list[str] = Field(default_factory=list)