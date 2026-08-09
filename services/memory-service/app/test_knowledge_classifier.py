from app.knowledge.classifier import (
    classify_knowledge,
)

from app.knowledge.knowledge_types import (
    KnowledgeDecision,
)


tests = [

    ([], KnowledgeDecision.NEW),

    ([("memory", 0.05)], KnowledgeDecision.REINFORCEMENT),

    ([("memory", 0.25)], KnowledgeDecision.RELATED),

    ([("memory", 0.80)], KnowledgeDecision.NEW),

]

for candidates, expected in tests:

    result = classify_knowledge(
        parsed_memory=None,
        candidates=candidates,
    )

    print(

        f"Expected: {expected.value}",

        f"Result: {result.value}",

    )