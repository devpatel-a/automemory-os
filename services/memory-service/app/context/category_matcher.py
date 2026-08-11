CATEGORY_KEYWORDS = {
    "preference": [
        "like",
        "love",
        "prefer",
        "favorite",
        "drink",
        "eat",
    ],
    "profile": [
        "name",
        "who",
        "live",
        "age",
        "location",
    ],
    "habit": [
        "daily",
        "habit",
        "usually",
        "every",
        "routine",
    ],
    "event": [
        "yesterday",
        "today",
        "tomorrow",
        "last",
        "next",
    ],
}


def category_match_score(
    query: str,
    memory_category: str,
) -> float:
    """
    Reward memories whose category
    matches the user's query.
    """

    query = query.lower()

    keywords = CATEGORY_KEYWORDS.get(
        memory_category.lower(),
        [],
    )

    for keyword in keywords:
        if keyword in query:
            return 0.15

    return 0.0