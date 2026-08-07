from app.intelligence.classifier import (
    classify,
    MemoryRelation,
)


tests = [

    ("Duplicate", 0.08),

    ("Reinforcement", 0.22),

    ("Related", 0.40),

    ("Independent", 0.75),
]

for label, distance in tests:

    result = classify(None, distance)

    print(label, "→", result.value)