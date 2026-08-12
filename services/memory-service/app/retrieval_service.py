from app.semantic.semantic_service import semantic_search
from app.ranking_service import calculate_score


def retrieve_memories(
    db,
    query: str,
    limit: int = 5,
):
    """
    Central retrieval entry point.

    Currently performs semantic retrieval.

    Future versions will merge:
    - Semantic Retrieval
    - Graph Retrieval

    without changing the public API.
    """

    semantic_results = semantic_search(
        db=db,
        query=query,
        limit=20,
    )

    candidates = []

    for memory, distance in semantic_results:

        candidates.append(
            {
                "memory": memory,
                "distance": distance,
                "score": calculate_score(
                    memory,
                    distance,
                ),
                "source": "semantic",
            }
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        (
            candidate["memory"],
            candidate["score"],
        )
        for candidate in candidates[:limit]
    ]