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
    include_archived: bool = False,
):
    """
    Perform semantic similarity search using pgvector.
    Allows passing a precomputed query_embedding to eliminate duplicate model calls.

    Lifecycle semantics (explicit, enforced at the source):
    - default: live memories only ('active' and 'weak'). Superseded historical
      memories stay 'active', so they remain available to historical queries.
    - include_archived=True: also archived memories (merged duplicates and
      contradicted claims) — for historical/audit/admin use.

    Returns:
        List[(Memory, distance)]
    """
    embedding = (
        query_embedding
        if query_embedding is not None
        else generate_embedding(query)
    )

    distance = Memory.embedding.cosine_distance(embedding)
    # Memories without an embedding are kept (distance NULL sorts last) so
    # they stay reachable, as before.
    q = db.query(Memory, distance.label("distance"))
    if not include_archived:
        q = q.filter(Memory.state != "archived")

    return q.order_by(distance).limit(limit).all()
