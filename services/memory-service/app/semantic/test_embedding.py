from sentence_transformers import SentenceTransformer

print("Loading model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Model loaded!")

sentence = "I love espresso."

embedding = model.encode(sentence)

print("\nSentence:")
print(sentence)

print("\nEmbedding Dimension:")
print(len(embedding))

print("\nFirst 10 Values:")
print(embedding[:10])