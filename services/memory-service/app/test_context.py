from app.database import SessionLocal

from app.context.context_engine import (
    ContextEngine,
)

db = SessionLocal()

engine = ContextEngine()

query = "Recommend a cafe"

print("\n========== QUERY ==========\n")

print(query)

context = engine.build_context(
    db=db,
    query=query,
)

print("\n========== CONTEXT ==========\n")

print(context)

print("\n========== SUCCESS ==========\n")