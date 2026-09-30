"""
Persistent knowledge-graph storage (PostgreSQL).

Identity is conservative: an entity is its normalized name
(normalize_entity_name). Different names are different entities unless an
explicit alias links them; embeddings never decide identity.
"""

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(50), server_default="CONCEPT")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EntityAlias(Base):
    """Explicit alias -> entity link. One alias names exactly one entity."""

    __tablename__ = "entity_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True,
    )
    alias_normalized: Mapped[str] = mapped_column(String(255), unique=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MemoryEntity(Base):
    """Which entities a memory mentions, and in what role (subject/value/mention)."""

    __tablename__ = "memory_entities"

    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True,
    )
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True,
    )
    role: Mapped[str] = mapped_column(String(20), server_default="mention")


class EntityRelationship(Base):
    """
    A typed edge between entities, supported by one memory. The same edge
    asserted by two memories is two rows of evidence, never a duplicate row.
    """

    __tablename__ = "entity_relationships"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(64))
    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), index=True,
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_entity_id", "target_entity_id", "relationship_type", "memory_id",
            name="uq_entity_relationships_edge_memory",
        ),
        CheckConstraint(
            "source_entity_id <> target_entity_id",
            name="ck_entity_relationships_no_self_link",
        ),
        Index("ix_entity_relationships_source_type", "source_entity_id", "relationship_type"),
    )
