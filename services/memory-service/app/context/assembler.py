from app.context.context_models import (
    ContextEvidence,
    ContextPackage,
    QueryIntent,
)

from app.context.models import (
    ContextCandidate,
)


def assemble_context(
    query: str,
    candidates: list[ContextCandidate],
    intent: QueryIntent | None = None,
) -> ContextPackage:
    """
    Convert ranked candidates into the
    final ContextPackage.
    """

    context = ContextPackage(
        query=query,
        intent=intent,
    )

    category_map = {
        "profile": context.profile,
        "preference": context.preferences,
        "habit": context.habits,
        "event": context.events,
    }

    for candidate in candidates:

        memory = candidate.memory

        bucket = category_map.get(
            memory.category,
            context.other,
        )

        bucket.append(
            memory.content,
        )

        context.evidence.append(
            build_evidence(candidate),
        )

    return context


def build_evidence(candidate: ContextCandidate) -> ContextEvidence:
    memory = candidate.memory
    fact = candidate.fact
    return ContextEvidence(
        memory_id=getattr(memory, "id", None),
        content=memory.content,
        category=getattr(memory, "category", None),
        entity=fact.entity if fact else None,
        attribute=fact.attribute if fact else None,
        value=fact.value if fact else None,
        temporal_state=candidate.temporal_state or (fact.temporal_state if fact else None),
        lifecycle_state=getattr(memory, "state", None),
        confidence=getattr(memory, "confidence", None),
        score=candidate.evidence_score or candidate.score,
        reasons=list(candidate.explanation),
        signals=candidate.retrieval.signals() if candidate.retrieval is not None else {},
    )
