from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

print("Loading model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

sentence1 = "Coffee is my favorite drink."
sentence2 = "I own a Tesla."

embedding1 = model.encode(sentence1)
embedding2 = model.encode(sentence2)

similarity = cos_sim(
    embedding1,
    embedding2,
)

print("\nSentence 1:")
print(sentence1)

print("\nSentence 2:")
print(sentence2)

print("\nCosine Similarity:")
print(float(similarity))