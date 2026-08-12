from enum import Enum


class MemoryAction(str, Enum):
    STORE = "store"
    REINFORCE = "reinforce"
    UPDATE = "update"
    MERGE = "merge"
    ARCHIVE = "archive"
    DELETE = "delete"
    IGNORE = "ignore"
    TRIGGER_AGENT = "trigger_agent"