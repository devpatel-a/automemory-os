from app.context.models import ContextCandidate


IMPORTANCE_WEIGHT = 0.25

ACCESS_WEIGHT = 0.20


def calculate_context_score(
    candidate: ContextCandidate,
) -> float:
    """
    Final ranking score for a
    retrieved memory.
    """

    memory = candidate.memory

    score = candidate.score

    score += memory.importance * IMPORTANCE_WEIGHT

    score += (

        min(
            memory.access_count / 10,
            1,
        )

        * ACCESS_WEIGHT

    )

    return score