from app.context.models import (
    ContextCandidate,
)


def diversify_candidates(
    candidates: list[ContextCandidate],
    limit: int = 5,
) -> list[ContextCandidate]:
    """
    Keep only one memory with identical content.
    Prevent duplicate context.
    """

    selected = []

    seen = set()

    for candidate in candidates:

        content = (
            candidate.memory.content
            .strip()
            .lower()
        )

        if content in seen:
            continue

        seen.add(content)

        selected.append(candidate)

        if len(selected) >= limit:
            break

    return selected