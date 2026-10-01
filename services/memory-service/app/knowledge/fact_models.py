from pydantic import BaseModel


class KnowledgeFact(BaseModel):
    """
    Structured, reusable knowledge fact representation across arbitrary domains.
    Extends v0.7 representation with temporal state, negation, and relationship context.
    Does NOT depend on database IDs during NLP extraction.
    """

    entity: str
    attribute: str
    value: str
    fact_type: str = "OTHER"
    temporal_info: str = "current"
    temporal_state: str = "CURRENT"  # CURRENT, HISTORICAL, FUTURE, UNKNOWN
    relationship_to_user: str | None = None  # e.g., friend, brother, colleague
    is_negated: bool = False
    # Extraction-quality flags (consumed by the knowledge_facts index only):
    # - is_placeholder: the entity or value only refers to something stated
    #   elsewhere ("I live there.", "I like them.", "We live in Pune.");
    # - is_question: the text asks rather than states ("Do I live in Pune?").
    is_placeholder: bool = False
    is_question: bool = False

    confidence: float = 0.60
    evidence_count: int = 1
    contradiction_count: int = 0

    # Runtime enrichment only (defaults to None during NLP extraction)
    superseded_by_id: int | None = None