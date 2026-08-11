from app.context.models import (
    ContextCandidate,
)


def rank_candidates(
    candidates: list[ContextCandidate],
):
    """
    Final ranking using all available signals.
    """

    for candidate in candidates:

        memory = candidate.memory

        candidate.score += (

            memory.importance * 0.25

            + min(
                memory.access_count / 10,
                1,
            ) * 0.20

        )

    candidates.sort(

        key=lambda candidate: candidate.score,

        reverse=True,

    )

    return candidates