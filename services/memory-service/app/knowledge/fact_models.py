from pydantic import BaseModel


class KnowledgeFact(BaseModel):
    """
    Structured, reusable knowledge fact representation across arbitrary domains.
    """

    entity: str
    attribute: str
    value: str
    fact_type: str = "OTHER"
    temporal_info: str = "current"

    confidence: float = 0.60

    evidence_count: int = 1

    contradiction_count: int = 0