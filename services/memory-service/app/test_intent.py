from app.understanding.intent_detector import detect_intent, MemoryIntent


def test_intent_detection():
    assert detect_intent("I like coffee.") == MemoryIntent.PREFERENCE
    assert detect_intent("I study Python every evening.") == MemoryIntent.HABIT
    assert detect_intent("I bought a Tesla yesterday.") == MemoryIntent.EVENT
    assert detect_intent("My name is Dev Patel.") == MemoryIntent.PROFILE
    assert detect_intent("The sky is blue.") == MemoryIntent.FACT