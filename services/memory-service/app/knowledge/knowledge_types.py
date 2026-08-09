from enum import Enum


class KnowledgeDecision(str, Enum):

    NEW = "new"

    REINFORCEMENT = "reinforcement"

    UPDATE = "update"

    CONTRADICTION = "contradiction"

    RELATED = "related"