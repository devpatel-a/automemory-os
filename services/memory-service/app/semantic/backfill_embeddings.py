from app.database import SessionLocal
from app.models import Memory
from app.semantic.semantic_service import generate_embedding

db = SessionLocal()

memories = (
    db.query(Memory)
    .filter(Memory.embedding.is_(None))
    .all()
)

print(f"Found {len(memories)} memories without embeddings.")

for memory in memories:
    print(f"Embedding: {memory.content}")

    memory.embedding = generate_embedding(memory.content)

db.commit()

print("✅ Backfill complete!")

db.close()