from semantic_service import generate_embedding

embedding = generate_embedding(
    "Coffee is my favorite drink."
)

print(type(embedding))
print(len(embedding))
print(embedding[:10])