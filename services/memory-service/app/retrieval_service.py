from app.semantic.semantic_service import semantic_search
from app.ranking_service import calculate_score


def retrieve_memories(
    db,
    query,
    limit=5,
):

    candidates = semantic_search(
        db,
        query,
        limit=20,
    )

    ranked = []

    for memory, distance in candidates:

        score = calculate_score(
            memory,
            distance,
        )

        ranked.append(
            (memory, score)
        )

    ranked.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return ranked[:limit]