from app.knowledge.temporal_cues import contains_cue

CATEGORY_MATCH_WEIGHT = 0.15


CATEGORY_KEYWORDS = {

    "profile": [
        "name",
        "who",
        "age",
        "live",
        "location",
    ],

    "preference": [
        "like",
        "love",
        "prefer",
        "favorite",
        "enjoy",
    ],

    "habit": [
        "daily",
        "every",
        "routine",
        "habit",
        "usually",
    ],

    "event": [
        "today",
        "yesterday",
        "tomorrow",
        "last",
        "next",
    ],

}


def category_match_score(
    query: str,
    category: str,
) -> float:
    """
    Reward memories whose category
    matches the user's query.
    """

    keywords = CATEGORY_KEYWORDS.get(category, [])

    # Whole-word cues ("like" must not match "likely"); inflections are listed.
    if keywords and contains_cue(query, keywords + [k + "s" for k in keywords]):
        return CATEGORY_MATCH_WEIGHT

    return 0.0