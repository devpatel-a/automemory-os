from pydantic import BaseModel, Field


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