from app.context.context_models import (
    ContextPackage,
)

from app.context.models import (
    ContextCandidate,
)


def assemble_context(
    query: str,
    candidates: list[ContextCandidate],
) -> ContextPackage:
    """
    Convert ranked candidates into the
    final ContextPackage.
    """

    context = ContextPackage(
        query=query,
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

    return context