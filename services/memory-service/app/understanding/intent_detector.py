from enum import Enum


class MemoryIntent(str, Enum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    HABIT = "habit"
    EVENT = "event"
    FACT = "fact"
    UNKNOWN = "unknown"


PREFERENCE_KEYWORDS = {
    "like",
    "love",
    "prefer",
    "favorite",
    "enjoy",
}

HABIT_KEYWORDS = {
    "every",
    "daily",
    "usually",
    "always",
    "often",
}

EVENT_KEYWORDS = {
    "visited",
    "went",
    "bought",
    "moved",
    "travelled",
    "traveled",
}

PROFILE_KEYWORDS = {
    "my name is",
    "i am",
    "i'm",
}


def detect_intent(
    text: str,
) -> MemoryIntent:
    """
    Detect the intent/category of
    a user memory.
    """

    sentence = text.lower()

    if any(keyword in sentence for keyword in PROFILE_KEYWORDS):
        return MemoryIntent.PROFILE

    if any(keyword in sentence for keyword in PREFERENCE_KEYWORDS):
        return MemoryIntent.PREFERENCE

    if any(keyword in sentence for keyword in HABIT_KEYWORDS):
        return MemoryIntent.HABIT

    if any(keyword in sentence for keyword in EVENT_KEYWORDS):
        return MemoryIntent.EVENT

    return MemoryIntent.FACT