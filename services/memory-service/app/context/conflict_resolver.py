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
}


def is_historical_query(query: str) -> bool:
    """Detect if query explicitly asks for historical or past context."""
    q_lower = query.lower()
    return any(kw in q_lower for kw in HISTORICAL_KEYWORDS)


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
    3. Fact Domain Resolution:
       - Prefers active/newer facts (based on state, created_at, lineage) over superseded facts.
       - Uses last_accessed only as a secondary tie-breaker.
    """
    if not candidates:
        return []

    historical = is_historical_query(query)

    # Step 1: Contradiction Lineage Lookup (contradicted_by_id)
    # Collect map of memory_id -> candidate
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

        # Contradiction Lineage check
        if is_contradicted or contradicted_by_id is not None:
            if not historical:
                c.explanation.append(
                    f"conflict_resolver: excluded (is_contradicted=True, superseded_by={contradicted_by_id})"
                )
                continue
            else:
                c.explanation.append(
                    f"conflict_resolver: retained historical fact (superseded_by={contradicted_by_id})"
                )

        # Merge Safety: Archived merged memories are excluded if active canonical exists
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

            if key in domain_map:
                existing_c = domain_map[key]
                existing_mem = existing_c.memory

                if not historical:
                    # Prefer active state
                    if getattr(mem, "state", None) == "active" and getattr(
                        existing_mem, "state", None
                    ) != "active":
                        domain_map[key] = c
                        c.explanation.append(
                            f"conflict_resolver: preferred active fact ({fact.value})"
                        )
                    # Prefer explicitly linked superseding memory
                    elif getattr(existing_mem, "contradicted_by_id", None) == mem.id:
                        domain_map[key] = c
                        c.explanation.append(
                            f"conflict_resolver: preferred superseding memory {mem.id}"
                        )
                    # Prefer created_at timestamp (fact creation time, not last_accessed)
                    elif getattr(mem, "created_at", None) and getattr(
                        existing_mem, "created_at", None
                    ):
                        if mem.created_at > existing_mem.created_at:
                            domain_map[key] = c
                            c.explanation.append(
                                f"conflict_resolver: preferred newer created fact ({fact.value})"
                            )
                        elif mem.created_at == existing_mem.created_at:
                            # Secondary tie-breaker: last_accessed
                            if getattr(mem, "last_accessed", None) and getattr(
                                existing_mem, "last_accessed", None
                            ):
                                if mem.last_accessed > existing_mem.last_accessed:
                                    domain_map[key] = c
                else:
                    # Historical query allows historical fact alongside current fact
                    resolved.append(c)
            else:
                domain_map[key] = c
        else:
            resolved.append(c)

    for c in domain_map.values():
        if c not in resolved:
            resolved.append(c)

    return resolved
