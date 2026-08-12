from sentence_transformers import SentenceTransformer

from app.models import Memory

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model ready.")


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for text.
    """
    return model.encode(text).tolist()


def semantic_search(
    db,
    query: str,
    limit: int = 20,
    query_embedding: list[float] | None = None,
):
    """
    Perform semantic similarity search using pgvector.
    Allows passing a precomputed query_embedding to eliminate duplicate model calls.

    Returns:
        List[(Memory, distance)]
    """
    embedding = (
        query_embedding
        if query_embedding is not None
        else generate_embedding(query)
    )

    results = (
        db.query(
            Memory,
            Memory.embedding.cosine_distance(embedding).label("distance"),
        )
        .order_by(Memory.embedding.cosine_distance(embedding))
        .limit(limit)
        .all()
    )

    return results