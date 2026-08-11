TEMPORAL_KEYWORDS = {
    "today": [
        "today",
    ],
    "yesterday": [
        "yesterday",
    ],
    "tomorrow": [
        "tomorrow",
    ],
    "last": [
        "last",
    ],
    "next": [
        "next",
    ],
}


def temporal_match_score(
    query: str,
    memory_content: str,
) -> float:
    """
    Reward memories that contain
    the same temporal expressions
    as the user query.
    """

    query = query.lower()
    memory = memory_content.lower()

    score = 0.0

    for keywords in TEMPORAL_KEYWORDS.values():

        for keyword in keywords:

            if (
                keyword in query
                and keyword in memory
            ):
                score += 0.15

    return score