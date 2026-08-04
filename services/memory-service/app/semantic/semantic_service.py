from sentence_transformers import SentenceTransformer

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model ready.")


def generate_embedding(text: str):
    return model.encode(text).tolist()