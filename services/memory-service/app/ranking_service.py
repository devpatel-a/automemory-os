def calculate_score(memory, distance):

    similarity = 1 - distance

    score = (
        similarity * 0.50
        + memory.importance * 0.25
        + min(memory.access_count / 10, 1.0) * 0.15
    )

    return score