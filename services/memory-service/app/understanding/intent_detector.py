from enum import Enum


class MemoryIntent(str, Enum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    HABIT = "habit"
    EVENT = "event"
    FACT = "fact"
    UNKNOWN = "unknown"


def detect_intent(text: str) -> MemoryIntent:

    sentence = text.lower()

    if any(word in sentence for word in [
        "like",
        "love",
        "prefer",
        "favorite",
    ]):
        return MemoryIntent.PREFERENCE

    if any(word in sentence for word in [
        "every",
        "usually",
        "always",
        "often",
    ]):
        return MemoryIntent.HABIT

    if any(word in sentence for word in [
        "bought",
        "visited",
        "went",
        "moved",
    ]):
        return MemoryIntent.EVENT

    if any(word in sentence for word in [
        "my name is",
        "i am",
        "i'm",
    ]):
        return MemoryIntent.PROFILE

    return MemoryIntent.FACT