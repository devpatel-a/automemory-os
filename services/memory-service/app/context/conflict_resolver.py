from app.context.models import ContextCandidate
from app.context.query_intent import CURRENT, FUTURE
from app.knowledge.attribute_schema import fact_domain_key
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory
from app.knowledge.temporal_cues import (
    FUTURE_QUERY_CUES,
    HISTORICAL_QUERY_CUES,
    contains_cue,
)

# Backward-compatible aliases; the cue lists live in app.knowledge.temporal_cues.
HISTORICAL_KEYWORDS = HISTORICAL_QUERY_CUES
FUTURE_KEYWORDS = FUTURE_QUERY_CUES


def is_historical_query(query: str) -> bool:
    """Detect if query explicitly asks for historical or past context."""
    return contains_cue(query, HISTORICAL_QUERY_CUES)


def is_future_query(query: str) -> bool:
    """Detect if query explicitly asks for future context."""
    return contains_cue(query, FUTURE_QUERY_CUES)


def resolve_conflicts(
    candidates: list[ContextCandidate],
    query: str,
    superseded_ids: set[int] | None = None,
) -> list[ContextCandidate]:
    """
    Resolves fact domain conflicts and applies state & contradiction safety filters:
    1. Contradiction Lineage (contradicted_by_id):
       - If A.contradicted_by_id == B.id, B is the superseding fact.
       - Filters out A for current queries. Retains A for historical queries.
    2. Merge Safety:
       - Merged archived memories (is_contradicted = False) are NOT treated as contradictions.
       - Active canonical memory is preferred.
    3. Temporal Intent Resolution:
       - Superseded lineage (MemoryRelationship 'superseded_by', passed as
         superseded_ids) makes a memory effectively HISTORICAL.
       - CURRENT query favors CURRENT facts over superseded/historical facts
         and never lets a FUTURE plan answer a current question.
       - HISTORICAL query retains and favors HISTORICAL facts.
       - FUTURE query favors FUTURE facts.
    """
    if not candidates:
        return []

    historical = is_historical_query(query)
    future_intent = is_future_query(query)

    # Step 1: Contradiction Lineage Lookup (contradicted_by_id)
    active_mids = {
        c.memory.id
        for c in candidates
        if getattr(c.memory, "state", None) == "active"
    }

    filtered_candidates = []
    for c in candidates:
        mem = c.memory
        state = getattr(mem, "state", "active")
        is_contradicted = getattr(mem, "is_contradicted", False)
        contradicted_by_id = getattr(mem, "contradicted_by_id", None)

        if is_contradicted or contradicted_by_id is not None:
            if not historical:
                c.explanation.append(
                    f"conflict_resolver: excluded contradicted (contradicted_by={contradicted_by_id})"
                )
                continue
            else:
                c.explanation.append(
                    f"conflict_resolver: retained contradicted fact for historical query (contradicted_by={contradicted_by_id})"
                )

        if state == "archived" and not is_contradicted:
            if active_mids:
                c.explanation.append(
                    "conflict_resolver: excluded (archived merged duplicate)"
                )
                continue

        filtered_candidates.append(c)

    if not filtered_candidates:
        return []

    # Step 2: Fact Domain Conflict Resolution
    # Facts compete per domain key: (entity, attribute) for single-valued
    # attributes, (entity, attribute, value) for multi-valued ones, so
    # coexisting preferences/devices are never collapsed into one.
    superseded = superseded_ids or set()
    domain_map = {}
    resolved = []

    for c in filtered_candidates:
        mem = c.memory
        fact = c.fact if c.fact is not None else extract_fact(parse_memory(mem.content))
        c.fact = fact

        if not (fact and fact.entity and fact.attribute):
            resolved.append(c)
            continue

        c.temporal_state = effective_temporal_state(mem, fact, superseded)
        if c.temporal_state != fact.temporal_state:
            c.explanation.append(
                f"conflict_resolver: effective temporal state {c.temporal_state} (superseded lineage)"
            )

        if historical:
            # Historical queries keep every temporal version of the fact.
            resolved.append(c)
            continue

        key = fact_domain_key(fact)
        existing_c = domain_map.get(key)
        if existing_c is None:
            domain_map[key] = c
            continue

        intent = FUTURE if future_intent else CURRENT
        if _prefers(c, existing_c, intent):
            domain_map[key] = c
            c.explanation.append(
                f"conflict_resolver: preferred {c.temporal_state} fact for {intent} query ({fact.value})"
            )
            existing_c.explanation.append("conflict_resolver: excluded (lost domain conflict)")
        else:
            c.explanation.append("conflict_resolver: excluded (lost domain conflict)")

    for c in domain_map.values():
        if c not in resolved:
            resolved.append(c)

    return resolved


# Preference order of effective temporal states per query temporal intent.
# A CURRENT query never lets a plan (FUTURE) or superseded fact displace a
# current fact; a FUTURE query prefers plans.
_TEMPORAL_PRIORITY = {
    CURRENT: {"CURRENT": 3, "UNKNOWN": 2, "HISTORICAL": 1, "FUTURE": 0},
    FUTURE: {"FUTURE": 3, "CURRENT": 2, "UNKNOWN": 1, "HISTORICAL": 0},
}


def effective_temporal_state(memory, fact, superseded_ids: set[int]) -> str:
    """Extracted temporal state, overridden to HISTORICAL by 'superseded_by' lineage."""
    if getattr(memory, "id", None) in superseded_ids:
        return "HISTORICAL"
    return fact.temporal_state if fact else "UNKNOWN"


def _prefers(new_c: ContextCandidate, old_c: ContextCandidate, intent: str) -> bool:
    """True if new_c should replace old_c as the answer for its fact domain."""
    priority = _TEMPORAL_PRIORITY[intent]
    new_rank = priority.get(new_c.temporal_state, 1)
    old_rank = priority.get(old_c.temporal_state, 1)
    if new_rank != old_rank:
        return new_rank > old_rank

    new_mem, old_mem = new_c.memory, old_c.memory
    # Explicit contradiction lineage
    if getattr(new_mem, "contradicted_by_id", None) == getattr(old_mem, "id", None):
        return False
    if getattr(old_mem, "contradicted_by_id", None) == getattr(new_mem, "id", None):
        return True

    # Otherwise the most recently stated fact wins. Rows written in one
    # transaction share created_at (Postgres now()), so fall back to the
    # monotonic id to keep "most recent" deterministic.
    new_created = getattr(new_mem, "created_at", None)
    old_created = getattr(old_mem, "created_at", None)
    if new_created and old_created and new_created != old_created:
        return new_created > old_created
    new_id = getattr(new_mem, "id", None)
    old_id = getattr(old_mem, "id", None)
    if new_id is not None and old_id is not None:
        return new_id > old_id
    return False
