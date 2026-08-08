from app.understanding.intent_detector import (
    detect_intent,
)

tests = [
    "I like coffee.",
    "I study Python every evening.",
    "I bought a Tesla yesterday.",
    "My name is Dev Patel.",
    "The sky is blue.",
]

for sentence in tests:

    print(sentence)

    print(
        "->",
        detect_intent(sentence).value,
    )

    print("-" * 40)