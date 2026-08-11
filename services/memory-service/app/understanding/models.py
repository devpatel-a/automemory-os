from pydantic import BaseModel, Field


class Entity(BaseModel):
    """
    Represents an extracted entity.
    """

    text: str
    label: str


class TemporalInfo(BaseModel):
    """
    Represents temporal information
    extracted from text.
    """

    category: str
    value: str


class ParsedMemory(BaseModel):
    """
    Final structured representation
    of a user memory.
    """

    content: str
    intent: str

    entities: list[Entity] = Field(
        default_factory=list
    )

    temporal: list[TemporalInfo] = Field(
        default_factory=list
    )