from app.understanding.temporal_parser import (
    extract_temporal_information,
)

tests = [

    "I study Python every evening.",

    "I bought a Tesla yesterday.",

    "I go to work every Monday.",

    "I wake up every day.",

    "I will travel next week.",
]

for sentence in tests:

    print(sentence)

    print(
        extract_temporal_information(
            sentence,
        )
    )

    print("-" * 40)