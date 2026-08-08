from app.intelligence.decision_types import (
    MemoryDecision,
)

from app.intelligence.decision_rules import (
    DECISION_RULES,
)


def decide(
    candidates,
):

    if not candidates:
        return MemoryDecision.NEW

    memory, distance = candidates[0]

    if distance is None:
        return MemoryDecision.NEW

    if distance <= DECISION_RULES["ignore"]:
        return MemoryDecision.IGNORE

    if distance <= DECISION_RULES["reinforce"]:
        return MemoryDecision.REINFORCE

    if distance <= DECISION_RULES["related"]:
        return MemoryDecision.RELATED

    return MemoryDecision.NEW