from pydantic import BaseModel


class KnowledgeFact(BaseModel):
    entity: str
    attribute: str
    value: str

    confidence: float = 0.60

    evidence_count: int = 1

    contradiction_count: int = 0