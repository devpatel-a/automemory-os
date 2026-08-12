from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryCreate(BaseModel):
    content: str
    category: str


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