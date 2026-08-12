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
    Rule-based contradiction detector.
    Handles Memory objects, (Memory, distance) tuples, and strings.
    """
    if isinstance(existing_memory, (tuple, list)):
        existing_memory = existing_memory[0]

    if isinstance(existing_memory, str):
        existing_text = existing_memory.lower()
    elif hasattr(existing_memory, "content"):
        existing_text = existing_memory.content.lower()
    else:
        return False

    new_text = new_memory.content.lower()

    for keyword in PROFILE_KEYWORDS:
        if (
            keyword in new_text
            and keyword in existing_text
            and new_text != existing_text
        ):
            return True

    return False