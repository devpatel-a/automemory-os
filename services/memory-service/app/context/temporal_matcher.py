from app.knowledge.temporal_cues import contains_cue

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

    score = 0.0

    for word in TEMPORAL_WORDS:

        # Whole words only ("last" must not match "lastly").
        if contains_cue(query, [word]) and contains_cue(memory_content, [word]):
            score += TEMPORAL_MATCH_WEIGHT

    return score