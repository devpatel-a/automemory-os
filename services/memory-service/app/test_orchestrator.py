from app.database import SessionLocal
from app.orchestrator.memory_orchestrator import (
    MemoryOrchestrator,
)

db = SessionLocal()

orchestrator = MemoryOrchestrator(db)

result = orchestrator.process(
    content="I love espresso.",
    category="preference",
    importance=0.80,
)

print(result)