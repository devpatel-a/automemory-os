from app.semantic.semantic_service import generate_embedding


def test_embedding_generation():
    sentence = "I love espresso."
    embedding = generate_embedding(sentence)
    assert isinstance(embedding, list)
    assert len(embedding) == 384