from sentence_transformers import SentenceTransformer
from sqlalchemy import text


from ..models import Memory


from sentence_transformers import SentenceTransformer
from app.models import Memory

model = SentenceTransformer("all-MiniLM-L6-v2")


def generate_embedding(text: str):
    return model.encode(text).tolist()


def semantic_search(db, query: str, limit: int = 20):

    embedding = generate_embedding(query)

    results = (
        db.query(
            Memory,
            Memory.embedding.cosine_distance(
                embedding
            ).label("distance"),
        )
        .order_by(
            Memory.embedding.cosine_distance(
                embedding
            )
        )
        .limit(limit)
        .all()
    )

    return results

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model ready.")


def generate_embedding(text: str):
    return model.encode(text).tolist()