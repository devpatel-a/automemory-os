"""
Synchronization, rebuild and consistency checks for the `knowledge_facts`
shadow index (design: docs/design/KNOWLEDGE_FACTS_INDEX.md, PR-1).

- `derive_fact_row(content)`: the pure derivation memories.content -> row
  values (or None), using the existing extractor unchanged.
- `sync_memory_fact(db, memory)`: idempotent upsert/delete for one memory,
  flushed inside the CALLER's transaction (never commits).
- `reindex(...)` / `check(...)`: explicit rebuild/backfill and audit utilities.

- `structural_candidates(db, fact, limit)`: evolution's structural candidate
  discovery. The index only NOMINATES memories; each one is re-validated
  against its canonical row (lifecycle, lineage and current content) before
  it is returned, and the classifier decides as before.

Retrieval and context assembly do not read the index. `lookup_fact_rows`
(tests/diagnostics) excludes placeholder facts, as the design requires.

CLI (from services/memory-service):
    python -m app.knowledge.fact_index reindex [--all] [--batch-size N]
    python -m app.knowledge.fact_index check
"""

import argparse
import hashlib
import json
import logging
import sys
from dataclasses import dataclass, field

from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.knowledge.attribute_schema import is_single_valued
from app.knowledge.fact_extractor import NO_ATTRIBUTE, extract_fact
from app.knowledge.fact_index_model import KnowledgeFactRow
from app.lineage import HISTORICAL_LINEAGE_TYPES
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.provenance.models import EXTRACTOR_VERSION
from app.understanding.memory_parser import parse_memory

logger = logging.getLogger(__name__)

KEY_LIMITS = {"entity_key": 255, "attribute_key": 128, "value_key": 255}


def content_sha256(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def fact_key(text: str) -> str:
    """Key normalization identical to the classifier's equality (strip + lower)."""
    return (text or "").strip().lower()


def derive_fact_row(content: str) -> dict | None:
    """
    Row values derived from memory text, or None when there is no usable fact:
    - extract_fact() found nothing, or
    - it found no attribute (the extractor's NO_ATTRIBUTE marker), or
    - the text is a question ("Do I live in Pune?" states nothing), or
    - a key would exceed its column (never truncated: no row, deterministically).

    Placeholder facts ("I live there.", "I like them.", "We live in Pune.")
    ARE stored, flagged is_placeholder, and excluded from lookups.
    """
    fact = extract_fact(parse_memory(content)) if content and content.strip() else None
    if fact is None or not fact.attribute or fact.attribute == NO_ATTRIBUTE or fact.is_question:
        return None

    row = {
        "entity_key": fact_key(fact.entity),
        "attribute_key": fact_key(fact.attribute),
        "value_key": fact_key(fact.value),
        "value_text": fact.value,
        "fact_type": fact.fact_type,
        "single_valued": is_single_valued(fact),
        "temporal_state": fact.temporal_state,
        "is_negated": fact.is_negated,
        "is_placeholder": fact.is_placeholder,
        "confidence": fact.confidence,
        "content_sha256": content_sha256(content),
        "extractor_version": EXTRACTOR_VERSION,
    }
    if not row["entity_key"] or not row["attribute_key"]:
        return None
    if any(len(row[k]) > limit for k, limit in KEY_LIMITS.items()):
        return None
    return row


def sync_memory_fact(db: Session, memory: Memory) -> dict | None:
    """
    Make memory's fact row match its current content (upsert, or delete when
    there is no usable fact). Flushes only: the caller's transaction commits or
    rolls back the fact row together with the content change.
    """
    row = derive_fact_row(memory.content)
    if row is None:
        db.execute(delete(KnowledgeFactRow).where(KnowledgeFactRow.memory_id == memory.id))
        return None
    stmt = pg_insert(KnowledgeFactRow.__table__).values(memory_id=memory.id, **row)
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=["memory_id"],
            set_={**row, "updated_at": stmt.excluded.updated_at},
        )
    )
    return row


def lookup_fact_rows(
    db: Session,
    entity: str,
    attribute: str,
    value: str | None = None,
    include_placeholders: bool = False,
) -> list[KnowledgeFactRow]:
    """
    Fact rows for (entity, attribute[, value]) using the composite index.
    Placeholder facts are excluded unless explicitly requested. Raw index
    rows, without canonical validation: tests and diagnostics only (evolution
    uses structural_candidates).
    """
    q = db.query(KnowledgeFactRow).filter(
        KnowledgeFactRow.entity_key == fact_key(entity),
        KnowledgeFactRow.attribute_key == fact_key(attribute),
    )
    if value is not None:
        q = q.filter(KnowledgeFactRow.value_key == fact_key(value))
    if not include_placeholders:
        q = q.filter(KnowledgeFactRow.is_placeholder.is_(False))
    return q.order_by(KnowledgeFactRow.memory_id).all()


# ------------------------------------------------- structural candidates

@dataclass
class StructuralLookup:
    """Validated structural candidates for one incoming fact."""

    memories: list[Memory] = field(default_factory=list)
    # More rows matched than the limit; the oldest were not examined.
    truncated: bool = False
    # Index rows whose canonical memory no longer supports them (stale/poisoned).
    rejected_ids: list[int] = field(default_factory=list)


def structural_candidates(db: Session, fact, limit: int) -> StructuralLookup:
    """
    Live memories whose indexed fact is in the incoming fact's domain:
    (entity, attribute) for single-valued attributes, where every value can
    conflict; (entity, attribute, value) for multi-valued ones, where only the
    same value can merge, reinforce, be negated or fulfil a plan.

    Discovery only, never a decision:
    - nothing is looked up for a missing/placeholder/question fact or limit <= 0;
    - placeholder rows are excluded;
    - lifecycle and lineage come from the canonical tables, not the index:
      archived, contradicted and historical-lineage (superseded_by /
      fulfilled_by) memories are excluded, exactly the memories evolution
      never acts on;
    - every nominated memory is re-derived from its CURRENT content and kept
      only if that content still places it in the domain, so a stale or
      poisoned row can never put an unrelated memory in front of the classifier;
    - deterministic: newest memory first; at most `limit` rows are examined and
      `truncated` reports when more matched.
    A memory whose row is missing is simply not nominated (semantic discovery
    still applies; `check` / `reindex` repair the index).
    """
    lookup = StructuralLookup()
    if (
        limit <= 0
        or fact is None
        or not fact.attribute
        or fact.attribute == NO_ATTRIBUTE
        or fact.is_placeholder
        or fact.is_question
    ):
        return lookup

    entity_key, attribute_key, value_key = fact_key(fact.entity), fact_key(fact.attribute), fact_key(fact.value)
    single_valued = is_single_valued(fact)
    historical = exists().where(
        MemoryRelationship.source_memory_id == Memory.id,
        MemoryRelationship.relationship_type.in_(HISTORICAL_LINEAGE_TYPES),
    )
    q = (
        db.query(Memory)
        .join(KnowledgeFactRow, KnowledgeFactRow.memory_id == Memory.id)
        .filter(
            KnowledgeFactRow.entity_key == entity_key,
            KnowledgeFactRow.attribute_key == attribute_key,
            KnowledgeFactRow.is_placeholder.is_(False),
            Memory.state != "archived",
            Memory.is_contradicted.isnot(True),
            ~historical,
        )
    )
    if not single_valued:
        q = q.filter(KnowledgeFactRow.value_key == value_key)
    memories = q.order_by(Memory.id.desc()).limit(limit + 1).all()
    if len(memories) > limit:
        lookup.truncated = True
        memories = memories[:limit]

    for memory in memories:
        canonical = derive_fact_row(memory.content)
        if (
            canonical is not None
            and not canonical["is_placeholder"]
            and canonical["entity_key"] == entity_key
            and canonical["attribute_key"] == attribute_key
            and (single_valued or canonical["value_key"] == value_key)
        ):
            lookup.memories.append(memory)
        else:
            lookup.rejected_ids.append(memory.id)

    if lookup.rejected_ids:
        logger.warning(
            "knowledge_facts rows not supported by their memory content (stale or "
            "inconsistent index; run `python -m app.knowledge.fact_index reindex`): %s",
            lookup.rejected_ids,
        )
    if lookup.truncated:
        logger.warning(
            "structural candidate limit %d reached for %s|%s; older domain members not examined",
            limit, entity_key, attribute_key,
        )
    return lookup


# ------------------------------------------------------------------ rebuild

def _stale_or_missing(memory: Memory, existing: KnowledgeFactRow | None) -> bool:
    if existing is None:
        return derive_fact_row(memory.content) is not None
    return (
        existing.content_sha256 != content_sha256(memory.content)
        or existing.extractor_version != EXTRACTOR_VERSION
    )


def reindex(session_factory, rebuild_all: bool = False, batch_size: int = 200) -> dict:
    """
    Backfill / rebuild knowledge_facts from memories.content.

    Idempotent and resumable. Processes memories in id order, one short
    transaction per batch. Each memory row is locked FOR UPDATE SKIP LOCKED,
    so rows being changed by a live evolution/PUT are skipped (their writer
    syncs them) and picked up by a later run. Never modifies memories,
    evidence, lineage or graph data.

    rebuild_all=False: only missing/stale rows (hash or extractor version);
    rebuild_all=True: recompute every memory.
    """
    stats = {"examined": 0, "written": 0, "deleted": 0, "skipped_locked": 0, "unchanged": 0}
    last_id = 0
    while True:
        session = session_factory()
        try:
            ids = [
                mid for (mid,) in session.execute(
                    select(Memory.id).where(Memory.id > last_id).order_by(Memory.id).limit(batch_size)
                ).all()
            ]
            if not ids:
                session.rollback()
                break
            last_id = ids[-1]
            locked = {
                m.id: m for m in session.query(Memory)
                .filter(Memory.id.in_(ids))
                .with_for_update(skip_locked=True)
                .all()
            }
            existing = {
                r.memory_id: r for r in session.query(KnowledgeFactRow)
                .filter(KnowledgeFactRow.memory_id.in_(ids)).all()
            }
            for mid in ids:
                stats["examined"] += 1
                memory = locked.get(mid)
                if memory is None:
                    stats["skipped_locked"] += 1
                    continue
                if not rebuild_all and not _stale_or_missing(memory, existing.get(mid)):
                    stats["unchanged"] += 1
                    continue
                if sync_memory_fact(session, memory) is None:
                    stats["deleted" if mid in existing else "unchanged"] += 1
                else:
                    stats["written"] += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    return stats


def check(db: Session) -> dict:
    """
    Report (never fix) index consistency with memories.content:
    - missing: memories that yield a fact but have no row
    - stale: rows whose content hash or extractor version does not match
    - unexpected: rows for memories that yield no usable fact
    """
    report = {"memories": 0, "rows": 0, "missing": [], "stale": [], "unexpected": []}
    rows = {r.memory_id: r for r in db.query(KnowledgeFactRow).all()}
    report["rows"] = len(rows)
    for memory in db.query(Memory).order_by(Memory.id).all():
        report["memories"] += 1
        row = rows.get(memory.id)
        derived = derive_fact_row(memory.content)
        if derived is None:
            if row is not None:
                report["unexpected"].append(memory.id)
        elif row is None:
            report["missing"].append(memory.id)
        elif (
            row.content_sha256 != derived["content_sha256"]
            or row.extractor_version != EXTRACTOR_VERSION
        ):
            report["stale"].append(memory.id)
    report["consistent"] = not (report["missing"] or report["stale"] or report["unexpected"])
    return report


def main(argv=None) -> int:
    from app.database import SessionLocal

    parser = argparse.ArgumentParser(description="knowledge_facts shadow index utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    rx = sub.add_parser("reindex", help="backfill/rebuild rows from memories.content")
    rx.add_argument("--all", action="store_true", help="recompute every memory, not only missing/stale")
    rx.add_argument("--batch-size", type=int, default=200)
    sub.add_parser("check", help="report missing/stale/unexpected rows (read-only)")
    args = parser.parse_args(argv)

    if args.command == "reindex":
        print(json.dumps(reindex(SessionLocal, rebuild_all=args.all, batch_size=args.batch_size)))
        return 0
    session = SessionLocal()
    try:
        report = check(session)
    finally:
        session.close()
    print(json.dumps(report))
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    sys.exit(main())
