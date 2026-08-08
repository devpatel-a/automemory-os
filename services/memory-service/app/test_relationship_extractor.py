from app.intelligence.decision_types import (
    MemoryDecision,
)

from app.intelligence.relationship_extractor import (
    extract_relationship,
)

for decision in MemoryDecision:

    print(
        decision.value,
        "->",
        extract_relationship(decision),
    )