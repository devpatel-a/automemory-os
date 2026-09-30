from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from .models import Memory
from .database import Base


class MemoryRelationship(Base):
    """
    Memory-to-memory lineage (see app/lineage.py): superseded_by, merged_into,
    fulfilled_by, ... A relationship is meaningless without both endpoints, so
    rows cascade when either memory is deleted.
    """

    __tablename__ = "memory_relationships"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    source_memory_id = Column(
        Integer,
        ForeignKey("memories.id", ondelete="CASCADE", name="fk_memory_relationships_source"),
        nullable=False,
    )

    target_memory_id = Column(
        Integer,
        ForeignKey("memories.id", ondelete="CASCADE", name="fk_memory_relationships_target"),
        nullable=False,
        index=True,
    )

    relationship_type = Column(
        String,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_memory_id",
            "target_memory_id",
            "relationship_type",
            name="uq_memory_relationships_source_target_type",
        ),
        CheckConstraint(
            "source_memory_id <> target_memory_id",
            name="ck_memory_relationships_no_self_link",
        ),
        Index(
            "ix_memory_relationships_source_type",
            "source_memory_id",
            "relationship_type",
        ),
    )
