"""
Provenance: why AutoMemory believes something.

Every statement processed by the pipeline appends one MemoryEvidence row to
the memory it produced or affected. Evidence is append-only: merges and
reinforcements add rows instead of overwriting, so the original statements
stay recoverable even when a canonical memory's text changes.
"""

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.database import Base

# Bump when extraction rules change so evidence records which rules produced a fact.
EXTRACTOR_VERSION = "deterministic-nlp-0.10"
DETERMINISTIC_NLP = "deterministic_nlp"
LEGACY_SOURCE = "legacy"


class MemoryEvidence(Base):
    __tablename__ = "memory_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"), index=True,
    )
    source_type: Mapped[str] = mapped_column(String(32))
    conversation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observed_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extractor_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Text the memory held before an administrative edit (PUT /memory/{id}).
    previous_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason_codes = mapped_column(JSONB, server_default=text("'[]'::jsonb"), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Provenance(BaseModel):
    """Caller-supplied origin of a statement (all optional except the source type)."""

    source_type: str = "api"
    conversation_id: str | None = None
    message_id: str | None = None
    observed_at: datetime | None = None
