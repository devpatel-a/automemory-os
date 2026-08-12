from app.intelligence.classifier import classify, MemoryRelation


def test_intelligence_classifier():
    tests = [
        (MemoryRelation.DUPLICATE, 0.08),
        (MemoryRelation.REINFORCEMENT, 0.22),
        (MemoryRelation.RELATED, 0.40),
        (MemoryRelation.INDEPENDENT, 0.75),
    ]
    for expected_relation, distance in tests:
        result = classify(None, distance)
        assert result == expected_relation