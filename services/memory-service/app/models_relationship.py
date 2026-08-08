from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)
from .models import Memory
from .database import Base


class MemoryRelationship(Base):

    __tablename__ = "memory_relationships"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    source_memory_id = Column(
        Integer,
        ForeignKey("memories.id"),
        nullable=False,
    )

    target_memory_id = Column(
        Integer,
        ForeignKey("memories.id"),
        nullable=False,
    )

    relationship_type = Column(
        String,
        nullable=False,
    )