from pydantic import BaseModel


class MemoryCreate(BaseModel):
    memory: str