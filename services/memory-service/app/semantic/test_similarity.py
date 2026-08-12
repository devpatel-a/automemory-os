from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim


def test_similarity_calculation():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    sentence1 = "Coffee is my favorite drink."
    sentence2 = "I love drinking coffee."
    embedding1 = model.encode(sentence1)
    embedding2 = model.encode(sentence2)
    similarity = float(cos_sim(embedding1, embedding2))
    assert similarity > 0.6