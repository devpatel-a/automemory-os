from pydantic import BaseModel, ConfigDict

from app.models import Memory


class ContextCandidate(BaseModel):
    """
    Represents a retrieved memory together
    with all scoring information used during
    context ranking.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )

    memory: Memory

    similarity: float

    score: float = 0.0