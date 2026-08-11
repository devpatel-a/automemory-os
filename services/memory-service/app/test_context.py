from app.database import SessionLocal

from app.context.context_engine import (
    ContextEngine,
)

db = SessionLocal()

engine = ContextEngine()

prompt = engine.build_context(
    db,
    "Recommend a cafe",
)

print(prompt)