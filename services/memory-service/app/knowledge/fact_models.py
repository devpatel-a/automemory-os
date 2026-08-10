from pydantic import BaseModel


class KnowledgeFact(BaseModel):
    entity: str
    attribute: str
    value: str