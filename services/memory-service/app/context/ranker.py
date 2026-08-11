from app.context.models import (
    ContextCandidate,
)

from app.context.scoring import (
    calculate_context_score,
)


def rank_candidates(
    candidates: list[ContextCandidate],
) -> list[ContextCandidate]:
    """
    Rank candidates by their
    final retrieval score.
    """

    for candidate in candidates:

        candidate.score = calculate_context_score(
            candidate,
        )

    return sorted(

        candidates,

        key=lambda candidate: candidate.score,

        reverse=True,

    )