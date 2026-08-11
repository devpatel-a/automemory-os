from app.context.models import (
    ContextCandidate,
)


def optimize_token_budget(
    candidates: list[ContextCandidate],
    max_characters: int = 1200,
) -> list[ContextCandidate]:
    """
    Approximate token budgeting
    using character count.
    """

    selected = []

    used = 0

    for candidate in candidates:

        length = len(
            candidate.memory.content,
        )

        if used + length > max_characters:
            break

        selected.append(candidate)

        used += length

    return selected