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
    created_at: datetime
    last_accessed: datetime

    model_config = ConfigDict(from_attributes=True)