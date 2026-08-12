from app.semantic.semantic_service import semantic_search
from app.ranking_service import calculate_score


def retrieve_memories(
    db,
    query: str,
    limit: int = 5,
):
    """
    Central retrieval API.

    Current sources:
        • Semantic Search

    Future sources:
        • Knowledge Graph
        • Hybrid Retrieval

    The public API will remain unchanged.
    """

    semantic_results = semantic_search(
        db=db,
        query=query,
        limit=20,
    )

    ranked = []

    for memory, distance in semantic_results:

        ranked.append(
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

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        (
            item["memory"],
            item["score"],
        )
        for item in ranked[:limit]
    ]