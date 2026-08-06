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

    similarity = 1 - distance

    if similarity >= SIMILARITY_THRESHOLD:
        return memory

    return None