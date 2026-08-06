from sqlalchemy import Integer, String, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .database import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True)

    content: Mapped[str] = mapped_column(Text)

    category: Mapped[str] = mapped_column(String(50))

    importance: Mapped[float] = mapped_column(Float, default=0.5)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

    access_count: Mapped[int] = mapped_column(Integer, default=0)

    state: Mapped[str] = mapped_column(
        String(20),
        default="active",
    )

    state: Mapped[str] = mapped_column(default="weak")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    last_accessed: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )