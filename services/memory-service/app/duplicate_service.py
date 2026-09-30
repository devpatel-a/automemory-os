import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.90


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

    if distance is None:
        return None

    similarity = 1 - distance

    logger.debug(
        "duplicate check: candidate=%r distance=%.4f similarity=%.4f",
        memory.content, distance, similarity,
    )

    if similarity >= SIMILARITY_THRESHOLD:
        return memory

    return None


def strengthen_memory(memory):
    """
    Strengthen an existing memory when
    a semantic duplicate is detected.
    """

    memory.importance = min(
        memory.importance + 0.05,
        1.0,
    )

    memory.access_count += 1

    memory.last_accessed = datetime.now(UTC)

    return memory