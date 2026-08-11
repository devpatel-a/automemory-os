from pydantic import BaseModel

from app.decision.decision_types import MemoryAction


class DecisionResult(BaseModel):
    action: MemoryAction
    reason: str