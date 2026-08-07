from app.semantic.semantic_service import (
    generate_embedding,
)

from sklearn.metrics.pairwise import cosine_similarity

from app.semantic.calibration_dataset import (
    TEST_CASES,
)

for first, second, label in TEST_CASES:

    emb1 = generate_embedding(first)
    emb2 = generate_embedding(second)

    score = cosine_similarity(
        [emb1],
        [emb2],
    )[0][0]

    print(
        f"{label:10}",
        f"{score:.3f}",
        "|",
        first,
        "<->",
        second,
    )