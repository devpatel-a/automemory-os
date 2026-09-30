import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.service import (
    calculate_importance,
    contradict_existing_memory,
    create_memory,
    lock_memory,
    merge_existing_memories,
    reinforce_existing_memory,
    supersede_existing_fact_memory,
    update_existing_fact_memory,
)
from app import lineage
from app.lineage import historical_memory_ids
from app.knowledge.fact_extractor import extract_fact
from app.models import Memory
from app.semantic.semantic_service import generate_embedding, semantic_search
from app.understanding.memory_parser import parse_memory
from app.knowledge.processor import process_knowledge
from app.knowledge.classifier import is_merge_equivalent
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.decision.decision_engine import decide
from app.graph.graph_service import GraphService
from app.provenance.models import (
    DETERMINISTIC_NLP,
    EXTRACTOR_VERSION,
    MemoryEvidence,
    Provenance,
)

logger = logging.getLogger(__name__)

# Candidate pool for evolution decisions, and the wider pool used only to
# resolve a contradiction target the classifier did not pin down.
CANDIDATE_LIMIT = 5
WIDE_CONTRADICTION_SEARCH_LIMIT = 50

# Attempts before giving up when concurrent writers keep changing the target.
MAX_ATTEMPTS = 3


class EvolutionConflict(RuntimeError):
    """The target memory changed concurrently; the evolution is retried from scratch."""


def get_memory_object(item):
    if hasattr(item, "content"):
        return item
    if hasattr(item, "__getitem__"):
        return item[0]
    return item


def is_memory_superseded(db: Session, memory_id: int) -> bool:
    """Check if a memory has historical lineage (superseded or fulfilled)."""
    if not memory_id:
        return False
    return memory_id in historical_memory_ids(db, [memory_id])


@dataclass
class _Evolution:
    memory: Memory
    reason_codes: list[str] = field(default_factory=list)


class MemoryPipeline:
    """
    AutoMemory OS Memory Pipeline

    Flow:
        User Input
            ↓
        Understanding Engine
            ↓
        Knowledge Engine  (decision + exact target + reason codes)
            ↓
        Decision Engine
            ↓
        Memory Engine: exactly one handler per knowledge decision,
                       executed atomically in one transaction
            ↓
        Knowledge Graph
    """

    def __init__(self, db: Session):
        self.db = db
        self.graph_service = GraphService(db)
        self._handlers = {
            KnowledgeDecision.NEW: self._store,
            KnowledgeDecision.RELATED: self._store,
            KnowledgeDecision.REINFORCEMENT: self._reinforce,
            KnowledgeDecision.UPDATE: self._update,
            KnowledgeDecision.SUPERSESSION: self._supersede,
            KnowledgeDecision.MERGE: self._merge,
            KnowledgeDecision.CONTRADICTION: self._contradict,
        }

    def process(
        self,
        content: str,
        category: str,
        provenance: Provenance | None = None,
    ):
        # 1. Understanding (and the one embedding this statement needs)
        parsed_memory = parse_memory(content)
        embedding = generate_embedding(content)

        # 2-5. Knowledge -> Decision -> Evolution, atomically; retried when a
        # concurrent writer changed the target between classification and write.
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                knowledge, decision, evolution = self._evolve(
                    content, category, parsed_memory, embedding, provenance,
                )
                self.db.commit()
                break
            except EvolutionConflict as conflict:
                self.db.rollback()
                logger.info("evolution conflict (attempt %d/%d): %s", attempt, MAX_ATTEMPTS, conflict)
                if attempt == MAX_ATTEMPTS:
                    raise
            except Exception:
                self.db.rollback()
                raise

        memory = evolution.memory
        self.db.refresh(memory)

        # 6b. Process-local graph view (compatibility; PostgreSQL is the source of truth)
        graph = self.graph_service.process_memory(
            parsed_memory=parsed_memory,
            memory_id=memory.id,
        )

        return {
            "memory": memory,
            "parsed": parsed_memory,
            "knowledge": knowledge,
            "decision": decision,
            "graph": graph,
            "reason_codes": evolution.reason_codes,
        }

    # ------------------------------------------------------------------ core

    def _evolve(self, content, category, parsed_memory, embedding, provenance=None):
        self.db.expire_all()
        candidates = semantic_search(
            self.db, content, limit=CANDIDATE_LIMIT, query_embedding=embedding,
        )
        by_id = {get_memory_object(c).id: get_memory_object(c) for c in candidates}
        historical = historical_memory_ids(self.db, by_id.keys())

        knowledge = process_knowledge(parsed_memory, candidates, historical)
        decision = decide(knowledge)
        target = by_id.get(knowledge.target_memory_id)

        handler = self._handlers[knowledge.decision]
        evolution = handler(
            content=content,
            category=category,
            parsed_memory=parsed_memory,
            embedding=embedding,
            candidates=candidates,
            historical=historical,
            target=target,
        )
        evolution.reason_codes = list(knowledge.reason_codes) + evolution.reason_codes
        evolution.reason_codes += self._link_fulfilled_plans(
            evolution.memory, knowledge.fact, candidates, historical,
        )

        # Provenance: append-only evidence for the memory this statement produced/affected
        self._record_evidence(evolution, knowledge, content, provenance)

        # 6a. Persistent knowledge graph, in the same transaction as the evolution
        self.graph_service.persist_memory(parsed_memory, evolution.memory.id)
        return knowledge, decision, evolution

    # -------------------------------------------------------------- handlers

    def _store(self, content, category, embedding, **_):
        memory = create_memory(
            content=content, category=category, db=self.db,
            embedding=embedding, commit=False,
        )
        return _Evolution(memory)

    def _reinforce(self, target, **context):
        if target is None:
            evolution = self._store(**context)
            evolution.reason_codes.append("reinforcement_target_unresolved")
            return evolution
        target = self._lock_live(target)
        return _Evolution(reinforce_existing_memory(self.db, target, commit=False))

    def _update(self, target, content, category, **context):
        if target is None:
            evolution = self._store(content=content, category=category, **context)
            evolution.reason_codes.append("update_target_unresolved")
            return evolution
        target = self._lock_live(target)
        return _Evolution(update_existing_fact_memory(self.db, target, content, category, commit=False))

    def _supersede(self, target, content, category, embedding, **context):
        if target is None:
            evolution = self._store(content=content, category=category, embedding=embedding)
            evolution.reason_codes.append("supersession_target_unresolved")
            return evolution

        target = self._lock_live(target)
        if is_memory_superseded(self.db, target.id):
            raise EvolutionConflict(f"memory {target.id} was superseded concurrently")

        # New memory for the new fact; the old one is preserved (state stays
        # 'active') for historical queries and linked via 'superseded_by'.
        memory = Memory(
            content=content,
            category=category,
            importance=calculate_importance(category),
            embedding=embedding,
            state="active",
        )
        self.db.add(memory)
        self.db.flush()
        supersede_existing_fact_memory(self.db, target, memory.id, commit=False)
        return _Evolution(memory, ["superseded_memory:%d" % target.id])

    def _merge(self, content, category, parsed_memory, embedding, candidates, historical, **_):
        merge_candidates = []
        for item in candidates:
            cm = get_memory_object(item)
            if cm.id in historical:
                continue
            dist = item[1] if hasattr(item, "__getitem__") and len(item) > 1 else None
            if is_merge_equivalent(parsed_memory, cm, distance=dist):
                merge_candidates.append(self._lock_live(cm))

        if not merge_candidates:
            evolution = self._store(content=content, category=category, embedding=embedding)
            evolution.reason_codes.append("merge_candidates_unresolved")
            return evolution

        memory = merge_existing_memories(
            self.db, merge_candidates, content, category,
            commit=False, embedding=embedding,
        )
        merged = [m.id for m in merge_candidates if m.id != memory.id]
        return _Evolution(memory, ["merged_memory:%d" % mid for mid in merged])

    def _contradict(self, target, content, category, parsed_memory, embedding, historical, **_):
        reasons = []
        if target is None:
            target = self._find_conflicting_memory(parsed_memory, embedding, historical)
            reasons.append(
                "contradiction_target_resolved_by_wide_search" if target is not None
                else "contradiction_target_unresolved"
            )
        if target is None:
            # Never lose the incoming claim, never archive an unrelated memory.
            logger.warning("contradiction without a resolvable target: %r", content)
            evolution = self._store(content=content, category=category, embedding=embedding)
            evolution.reason_codes.extend(reasons)
            return evolution

        target = self._lock_live(target)

        # The incoming claim is a competing statement: never fold it into a
        # different similar memory. An exact re-assertion of a previously
        # contradicted statement reactivates that memory (create_memory).
        memory = create_memory(
            content=content, category=category, db=self.db,
            embedding=embedding, semantic_dedupe=False, commit=False,
        )
        if memory.id == target.id:
            reasons.append("reasserted_existing_memory")
            return _Evolution(memory, reasons)

        contradict_existing_memory(self.db, target, memory.id, commit=False)
        reasons.append("contradicted_memory:%d" % target.id)
        return _Evolution(memory, reasons)

    # --------------------------------------------------------------- helpers

    def _record_evidence(self, evolution, knowledge, content, provenance) -> None:
        provenance = provenance or Provenance()
        evidence = MemoryEvidence(
            memory_id=evolution.memory.id,
            source_type=provenance.source_type,
            conversation_id=provenance.conversation_id,
            message_id=provenance.message_id,
            extraction_method=DETERMINISTIC_NLP,
            extractor_version=EXTRACTOR_VERSION,
            confidence=knowledge.fact.confidence if knowledge.fact is not None else None,
            raw_text=content,
            decision=knowledge.decision.value,
            reason_codes=list(evolution.reason_codes),
        )
        if provenance.observed_at is not None:
            evidence.observed_at = provenance.observed_at
        self.db.add(evidence)
        self.db.flush()

    def _link_fulfilled_plans(self, memory, fact, candidates, historical) -> list[str]:
        """
        A CURRENT, non-negated fact that matches a stored FUTURE plan (same
        entity, attribute and value) is evidence the plan happened: link
        plan --fulfilled_by--> fact. The plan stays stored and queryable, but
        is effectively HISTORICAL from then on. Time passing alone never does this.
        """
        if fact is None or fact.temporal_state != "CURRENT" or fact.is_negated or not fact.attribute:
            return []
        key = (fact.entity.strip().lower(), fact.attribute.strip().lower(), fact.value.strip().lower())
        reasons = []
        for item in candidates:
            plan = get_memory_object(item)
            if plan.id == memory.id or plan.id in historical or plan.state == "archived":
                continue
            plan_fact = extract_fact(parse_memory(plan.content))
            if plan_fact is None or plan_fact.temporal_state != "FUTURE" or plan_fact.is_negated:
                continue
            plan_key = (
                plan_fact.entity.strip().lower(),
                plan_fact.attribute.strip().lower(),
                plan_fact.value.strip().lower(),
            )
            if plan_key == key:
                lineage.link(self.db, plan.id, memory.id, lineage.FULFILLED_BY)
                reasons.append("fulfilled_plan:%d" % plan.id)
        return reasons

    def _lock_live(self, memory: Memory) -> Memory:
        """Row-lock a target and verify it is still a live evolution target."""
        locked = lock_memory(self.db, memory)
        if locked.state == "archived" or locked.is_contradicted:
            raise EvolutionConflict(f"memory {locked.id} was archived or contradicted concurrently")
        return locked

    def _find_conflicting_memory(self, parsed_memory, embedding, historical):
        """Wider search for the live memory an incoming claim contradicts."""
        wide = semantic_search(
            self.db, parsed_memory.content,
            limit=WIDE_CONTRADICTION_SEARCH_LIMIT, query_embedding=embedding,
        )
        wide_historical = historical | historical_memory_ids(
            self.db, [get_memory_object(c).id for c in wide]
        )
        for item in wide:
            memory = get_memory_object(item)
            if memory.id in wide_historical:
                continue
            if detect_contradiction(parsed_memory, memory):
                return memory
        return None
