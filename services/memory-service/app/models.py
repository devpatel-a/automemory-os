from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func as sa_func,
    literal_column,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .database import Base

# Vector dimension of memories.embedding. Changing it requires a migration;
# the configured embedding model must produce vectors of this size
# (validated at startup, see app/startup.py).
EMBEDDING_DIMENSION = 384


MEMORY_STATES = ("active", "weak", "archived")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True)

    content: Mapped[str] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(50))

    importance: Mapped[float] = mapped_column(Float, default=0.5)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
    )

    access_count: Mapped[int] = mapped_column(Integer, default=0)

    state: Mapped[str] = mapped_column(
        String(20),
        default="active",
        index=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        default=1.0,
    )

    contradicted_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("memories.id", ondelete="SET NULL", name="fk_memories_contradicted_by"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    last_accessed: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    is_contradicted: Mapped[bool] = mapped_column(
        default=False
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('active', 'weak', 'archived')",
            name="ck_memories_state",
        ),
        CheckConstraint(
            "contradicted_by_id IS NULL OR contradicted_by_id <> id",
            name="ck_memories_not_self_contradicted",
        ),
        # Lexical retrieval (PostgreSQL full-text search)
        Index(
            "ix_memories_content_fts",
            sa_func.to_tsvector(literal_column("'english'"), literal_column("content")),
            postgresql_using="gin",
        ),
    )
