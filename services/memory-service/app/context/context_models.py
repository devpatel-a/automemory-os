from pydantic import BaseModel


class ContextPackage(BaseModel):
    query: str

    profile: list[str] = []

    preferences: list[str] = []

    habits: list[str] = []

    events: list[str] = []

    other: list[str] = []