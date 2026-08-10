from app.understanding.memory_parser import (
    parse_memory,
)

from app.knowledge.fact_extractor import (
    extract_fact,
)

tests = [

    "I live in Pune.",

    "My favorite drink is coffee.",

]

for sentence in tests:

    parsed = parse_memory(sentence)

    fact = extract_fact(parsed)

    print(sentence)

    print(fact)

    print("-" * 40)