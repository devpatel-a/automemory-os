from app.intelligence.decision_engine import decide

tests = [

    ([], "new"),

    ([(None, 0.03)], "ignore"),

    ([(None, 0.15)], "reinforce"),

    ([(None, 0.35)], "related"),

    ([(None, 0.80)], "new"),
]

for candidates, expected in tests:

    result = decide(candidates)

    print(
        expected,
        "->",
        result.value,
    )