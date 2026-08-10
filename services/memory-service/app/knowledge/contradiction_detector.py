from app.understanding.models import ParsedMemory


PROFILE_KEYWORDS = [
    "live",
    "name",
    "age",
    "born",
]


def detect_contradiction(
    new_memory: ParsedMemory,
    existing_memory,
) -> bool:
    """
    Very first contradiction detector.

    Rule-based.
    """

    new_text = new_memory.content.lower()

    existing_text = existing_memory.content.lower()

    for keyword in PROFILE_KEYWORDS:

        if (
            keyword in new_text
            and keyword in existing_text
            and new_text != existing_text
        ):
            return True

    return False