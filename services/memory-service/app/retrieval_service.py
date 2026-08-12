from app.semantic.semantic_service import semantic_search
from app.ranking_service import calculate_score


def retrieve_memories(
    db,
    query: str,
    limit: int = 5,
):
    """
    Retrieve the most relevant memories.

    Pipeline:
        1. Semantic Search
        2. Ranking
        3. Sort
        4. Return Top-K

    Graph retrieval will be plugged into this
    function in the next milestone.
    """

    semantic_results = semantic_search(
        db=db,
        query=query,
        limit=20,
    )

    candidates = []

    for memory, distance in semantic_results:

        score = calculate_score(
            memory=memory,
            distance=distance,
        )

        candidates.append(
            {
                "memory": memory,
                "distance": distance,
                "score": score,
                "source": "semantic",
            }
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return [
        (item["memory"], item["score"])
        for item in candidates[:limit]
    ]