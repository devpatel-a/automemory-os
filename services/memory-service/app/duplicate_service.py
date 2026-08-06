from datetime import UTC, datetime

SIMILARITY_THRESHOLD = 0.90

def strengthen_memory(memory):

    memory.importance = min(
        memory.importance + 0.05,
        1.0,
    )

    memory.access_count += 1

    memory.last_accessed = datetime.now(UTC)

    return memory

def find_duplicate(candidates):
    """
    candidates:
    [
        (memory, distance),
        ...
    ]
    """

    if not candidates:
        return None

    memory, distance = candidates[0]

    similarity = 1 - distance

    if similarity >= SIMILARITY_THRESHOLD:
        return memory

    return None