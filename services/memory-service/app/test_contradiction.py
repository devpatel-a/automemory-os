from app.models import Memory

from app.understanding.memory_parser import (
    parse_memory,
)

from app.knowledge.contradiction_detector import (
    detect_contradiction,
)

existing = Memory(
    content="I live in Mumbai."
)

new = parse_memory(
    "I live in Pune."
)

print(

    detect_contradiction(
        new,
        existing,
    )

)