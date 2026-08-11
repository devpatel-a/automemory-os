from app.models import Memory


def calculate_context_score(
    memory: Memory,
    similarity: float,
) -> float:
    """
    Combine multiple signals into one score.
    """

    importance = memory.importance
    accesses = min(memory.access_count / 10.0, 1.0)

    score = (
        similarity * 0.60
        + importance * 0.30
        + accesses * 0.10
    )

    return round(score, 4)