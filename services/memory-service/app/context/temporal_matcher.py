TEMPORAL_MATCH_WEIGHT = 0.15


TEMPORAL_WORDS = [

    "today",

    "yesterday",

    "tomorrow",

    "last",

    "next",

]


def temporal_match_score(
    query: str,
    memory_content: str,
) -> float:
    """
    Reward memories that share
    temporal expressions with
    the query.
    """

    query = query.lower()

    memory = memory_content.lower()

    score = 0.0

    for word in TEMPORAL_WORDS:

        if word in query and word in memory:
            score += TEMPORAL_MATCH_WEIGHT

    return score