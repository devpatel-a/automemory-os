from pydantic import BaseModel


from pydantic import BaseModel


class MemoryCreate(BaseModel):
    content: str
    category: str