from enum import Enum
from .rules import RULES


def classify(memory, distance):

    if distance is None:
        return MemoryRelation.INDEPENDENT

    if distance <= RULES["duplicate_distance"]:
        return MemoryRelation.DUPLICATE

    if distance <= RULES["reinforcement_distance"]:
        return MemoryRelation.REINFORCEMENT

    if distance <= RULES["related_distance"]:
        return MemoryRelation.RELATED

    return MemoryRelation.INDEPENDENT

class MemoryRelation(str, Enum):
    DUPLICATE = "duplicate"
    REINFORCEMENT = "reinforcement"
    RELATED = "related"
    CONTRADICTION = "contradiction"
    INDEPENDENT = "independent"