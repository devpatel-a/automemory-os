from app.database import SessionLocal

from app.retrieval_service import retrieve_memories

db = SessionLocal()

results = retrieve_memories(
    db,
    "I like beverages",
)

print()

print("===== Retrieval Results =====")

for memory, score in results:

    print()

    print(memory.content)

    print(score)