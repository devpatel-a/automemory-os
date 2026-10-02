"""
`knowledge_facts`: a derived, rebuildable structural index over memories.

memories.content is the source of truth. Each row is the structured fact that
`extract_fact` derives from a memory's CURRENT text, witnessed by
`content_sha256` and `extractor_version` (design: docs/design/KNOWLEDGE_FACTS_INDEX.md).

Deliberately NOT stored: lifecycle (state, contradiction) or lineage
(superseded/fulfilled). Those stay owned by `memories` and
`memory_relationships` and are joined at query time, so this table can never
become a second source of truth for memory state.

Read by evolution only to DISCOVER candidates (fact_index.structural_candidates),
each re-validated against its memory; never read by retrieval, never a
decision input on its own.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class KnowledgeFactRow(Base):
    __tablename__ = "knowledge_facts"

    # 0..1 row per memory (extract_fact yields at most one fact); cascades on purge.
    memory_id: Mapped[int] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE", name="fk_knowledge_facts_memory"),
        primary_key=True,
    )
    entity_key: Mapped[str] = mapped_column(String(255))
    attribute_key: Mapped[str] = mapped_column(String(128))
    value_key: Mapped[str] = mapped_column(String(255))
    value_text: Mapped[str] = mapped_column(Text)
    fact_type: Mapped[str] = mapped_column(String(32))
    single_valued: Mapped[bool] = mapped_column(Boolean)
    # The EXTRACTED temporal state, never the effective (lineage-aware) one.
    temporal_state: Mapped[str] = mapped_column(String(16))
    is_negated: Mapped[bool] = mapped_column(Boolean)
    is_placeholder: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float)
    content_sha256: Mapped[str] = mapped_column(String(64))
    extractor_version: Mapped[str] = mapped_column(String(32))
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_knowledge_facts_domain_value", "entity_key", "attribute_key", "value_key"),
        CheckConstraint(
            "temporal_state IN ('CURRENT', 'HISTORICAL', 'FUTURE', 'UNKNOWN')",
            name="ck_knowledge_facts_temporal_state",
        ),
        CheckConstraint(
            "entity_key <> '' AND attribute_key <> ''",
            name="ck_knowledge_facts_keys_not_empty",
        ),
        CheckConstraint(
            "char_length(content_sha256) = 64",
            name="ck_knowledge_facts_content_sha256",
        ),
    )
