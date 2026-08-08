from enum import Enum


class MemoryDecision(str, Enum):
    NEW = "new"

    REINFORCE = "reinforce"

    UPDATE = "update"

    RELATED = "related"

    IGNORE = "ignore"