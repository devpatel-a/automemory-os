from app.intelligence.classifier import (
    MemoryRelation,
)

from app.intelligence.actions import (
    execute_action,
)

for relation in MemoryRelation:

    print(
        relation.value,
        "->",
        execute_action(relation).value,
    )