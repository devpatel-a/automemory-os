from enum import Enum

from .classifier import MemoryRelation


class MemoryAction(str, Enum):
    MERGE = "merge"
    REINFORCE = "reinforce"
    LINK = "link"
    STORE = "store"
    CONTRADICT = "contradict"


def relation_to_action(
    relation: MemoryRelation,
) -> MemoryAction:

    mapping = {
        MemoryRelation.DUPLICATE: MemoryAction.MERGE,
        MemoryRelation.REINFORCEMENT: MemoryAction.REINFORCE,
        MemoryRelation.RELATED: MemoryAction.LINK,
        MemoryRelation.INDEPENDENT: MemoryAction.STORE,
        MemoryRelation.CONTRADICTION: MemoryAction.CONTRADICT,
    }

    return mapping[relation]


def execute_action(
    relation: MemoryRelation,
) -> MemoryAction:

    action = relation_to_action(relation)

    return action