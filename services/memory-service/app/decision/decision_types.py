from enum import Enum


class MemoryAction(str, Enum):
    STORE = "store"
    REINFORCE = "reinforce"
    UPDATE = "update"
    ARCHIVE = "archive"
    DELETE = "delete"
    IGNORE = "ignore"
    TRIGGER_AGENT = "trigger_agent"