from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    """Structural interpretation of a query (see app.context.query_intent)."""

    entity: str | None = None
    attribute: str | None = None
    temporal_intent: str = "CURRENT"


class ContextEvidence(BaseModel):
    """
    Machine-readable evidence for one selected memory: what fact it states,
    its temporal/lifecycle state, confidence, and why it was selected.
    """

    memory_id: int | None = None
    content: str
    category: str | None = None
    entity: str | None = None
    attribute: str | None = None
    value: str | None = None
    temporal_state: str | None = None
    lifecycle_state: str | None = None
    confidence: float | None = None
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class ContextPackage(BaseModel):
    """
    Final structured context returned by
    the Context Engine.
    """

    query: str

    profile: list[str] = Field(
        default_factory=list
    )

    preferences: list[str] = Field(
        default_factory=list
    )

    habits: list[str] = Field(
        default_factory=list
    )

    events: list[str] = Field(
        default_factory=list
    )

    other: list[str] = Field(
        default_factory=list
    )

    # Structured, backward-compatible extensions (v0.9)
    intent: QueryIntent | None = None

    evidence: list[ContextEvidence] = Field(
        default_factory=list
    )
