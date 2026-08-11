from pydantic import BaseModel


class Entity(BaseModel):
    text: str
    label: str


class TemporalInfo(BaseModel):
    category: str
    value: str


class ParsedMemory(BaseModel):
    content: str
    intent: str
    entities: list[Entity]
    temporal: list[TemporalInfo]