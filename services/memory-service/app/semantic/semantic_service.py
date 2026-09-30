import logging

from sentence_transformers import SentenceTransformer

from app.config import settings
from app.models import EMBEDDING_DIMENSION, Memory

logger = logging.getLogger(__name__)


class EmbeddingDimensionMismatch(RuntimeError):
    pass


logger.info("Loading embedding model %s", settings.embedding_model)
model = SentenceTransformer(settings.embedding_model)


def embedding_dimension() -> int:
    """Dimension of vectors produced by the configured embedding model."""
    return int(model.get_sentence_embedding_dimension())


def generate_embedding(text: str) -> list[float]:
    """
    Generate a vector embedding for text.
    """
    vector = model.encode(text).tolist()
    if len(vector) != EMBEDDING_DIMENSION:
        raise EmbeddingDimensionMismatch(
            f"Embedding model '{settings.embedding_model}' produced {len(vector)}-dimensional "
            f"vectors but memories.embedding is vector({EMBEDDING_DIMENSION})."
        )
    return vector


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