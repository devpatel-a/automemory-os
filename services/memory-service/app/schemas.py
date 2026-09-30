from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryCreate(BaseModel):
    content: str
    category: str
    # Optional provenance (additive; defaults keep the previous request shape valid)
    source_type: str = "api"
    conversation_id: str | None = None
    message_id: str | None = None
    observed_at: datetime | None = None


class MemoryUpdate(BaseModel):
    content: str


class MemoryResponse(BaseModel):
    id: int
    content: str
    category: str
    importance: float
    access_count: int
    state: str
    confidence: float = 1.0
    is_contradicted: bool = False
    created_at: datetime
    last_accessed: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class AgentQueryResponse(BaseModel):
    query: str
    prompt: str
    response: str
    memories_used: list[MemoryResponse]
    reflection: dict | None = None


class EvidenceResponse(BaseModel):
    id: int
    source_type: str
    conversation_id: str | None = None
    message_id: str | None = None
    observed_at: datetime
    extraction_method: str | None = None
    extractor_version: str | None = None
    confidence: float | None = None
    raw_text: str | None = None
    decision: str | None = None
    reason_codes: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class LineageLink(BaseModel):
    relationship_type: str
    memory_id: int
    content: str


class MemoryEvidenceResponse(BaseModel):
    """Why AutoMemory believes a memory: its evidence and its lineage."""

    memory: MemoryResponse
    evidence: list[EvidenceResponse]
    outgoing: list[LineageLink]       # e.g. superseded_by / merged_into / fulfilled_by
    incoming: list[LineageLink]       # e.g. memories this one superseded or absorbed
    contradicted_by: LineageLink | None = None
