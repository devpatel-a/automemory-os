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
        "drink",
        "eat",
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

    query = query.lower()

    for keyword in CATEGORY_KEYWORDS.get(
        category,
        [],
    ):

        if keyword in query:
            return CATEGORY_MATCH_WEIGHT

    return 0.0