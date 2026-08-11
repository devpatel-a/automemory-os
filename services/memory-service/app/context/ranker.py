from app.context.models import (
    ContextCandidate,
)


def rank_candidates(
    candidates: list[ContextCandidate],
):

    for candidate in candidates:

        memory = candidate.memory

        candidate.score = (

            candidate.similarity * 0.55

            + memory.importance * 0.25

            + min(
                memory.access_count / 10,
                1,
            )
            * 0.20

        )

    candidates.sort(

        key=lambda x: x.score,

        reverse=True,

    )

    return candidates