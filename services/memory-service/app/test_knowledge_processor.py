from app.understanding.memory_parser import (
    parse_memory,
)

from app.knowledge.processor import (
    process_knowledge,
)

parsed = parse_memory(

    "My favorite drink is coffee."

)

result = process_knowledge(

    parsed,

    [],

)

print(result)