from enum import Enum


class KnowledgeDecision(str, Enum):
    NEW = "new"
    REINFORCEMENT = "reinforcement"
    UPDATE = "update"
    MERGE = "merge"
    CONTRADICTION = "contradiction"
    SUPERSESSION = "supersession"
    RELATED = "related"