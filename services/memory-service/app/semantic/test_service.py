from app.semantic.semantic_service import generate_embedding


def test_semantic_service_generate_embedding():
    embedding = generate_embedding("Coffee is my favorite drink.")
    assert isinstance(embedding, list)
    assert len(embedding) == 384