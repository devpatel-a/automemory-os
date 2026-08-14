from app.context.models import ContextCandidate
from app.knowledge.fact_extractor import extract_fact
from app.understanding.memory_parser import parse_memory

HISTORICAL_KEYWORDS = {
    "before",
    "previously",
    "past",
    "history",
    "used to",
    "formerly",
    "lived in",
    "was",
    "earlier",
    "did i",
}

FUTURE_KEYWORDS = {
    "will",
    "going to",
    "future",
    "next year",
    "tomorrow",
    "plan to",
}


def is_historical_query(query: str) -> bool:
    """Detect if query explicitly asks for historical or past context."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in HISTORICAL_KEYWORDS)


def is_future_query(query: str) -> bool:
    """Detect if query explicitly asks for future context."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in FUTURE_KEYWORDS)


def resolve_conflicts(
    candidates: list[ContextCandidate],
    query: str,
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
       - CURRENT query favors CURRENT facts over superseded/historical facts.
       - HISTORICAL query retains and favors HISTORICAL facts.
       - FUTURE query favors FUTURE facts.
    """
    if not candidates:
        return []

    historical = is_historical_query(query)
    future_intent = is_future_query(query)

    # Step 1: Contradiction Lineage Lookup (contradicted_by_id)
    cand_map = {c.memory.id: c for c in candidates if hasattr(c.memory, "id")}
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
                    f"conflict_resolver: excluded superseded (superseded_by={contradicted_by_id})"
                )
                continue
            else:
                c.explanation.append(
                    f"conflict_resolver: retained historical fact (superseded_by={contradicted_by_id})"
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

    # Step 2: Fact Domain Conflict Resolution (Same entity + attribute)
    domain_map = {}
    resolved = []

    for c in filtered_candidates:
        mem = c.memory
        parsed = parse_memory(mem.content)
        fact = extract_fact(parsed)

        if fact and fact.entity and fact.attribute:
            key = (fact.entity.lower(), fact.attribute.lower())
            mem_temporal = fact.temporal_state

            if key in domain_map:
                existing_c = domain_map[key]
                existing_mem = existing_c.memory
                existing_fact = extract_fact(parse_memory(existing_mem.content))
                existing_temporal = existing_fact.temporal_state if existing_fact else "CURRENT"

                if historical:
                    # Historical query allows historical facts alongside current facts
                    resolved.append(c)
                elif future_intent:
                    if mem_temporal == "FUTURE" and existing_temporal != "FUTURE":
                        domain_map[key] = c
                        c.explanation.append("conflict_resolver: preferred future fact")
                    elif getattr(mem, "created_at", None) and getattr(existing_mem, "created_at", None):
                        if mem.created_at > existing_mem.created_at:
                            domain_map[key] = c
                else:
                    # Current query prefers CURRENT fact over HISTORICAL fact
                    if mem_temporal == "CURRENT" and existing_temporal == "HISTORICAL":
                        domain_map[key] = c
                        c.explanation.append(f"conflict_resolver: preferred current fact ({fact.value})")
                    elif getattr(mem, "contradicted_by_id", None) == existing_mem.id:
                        pass # existing_mem supersedes mem
                    elif getattr(existing_mem, "contradicted_by_id", None) == mem.id:
                        domain_map[key] = c
                    elif getattr(mem, "created_at", None) and getattr(existing_mem, "created_at", None):
                        if mem.created_at > existing_mem.created_at:
                            domain_map[key] = c
            else:
                domain_map[key] = c
        else:
            resolved.append(c)

    for c in domain_map.values():
        if c not in resolved:
            resolved.append(c)

    return resolved
