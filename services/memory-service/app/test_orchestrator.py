from app.database import SessionLocal
from app.orchestrator.memory_orchestrator import MemoryOrchestrator


def test_memory_orchestrator():
    db = SessionLocal()
    try:
        orchestrator = MemoryOrchestrator(db)
        result = orchestrator.process(
            content="I love espresso.",
            category="preference",
            importance=0.80,
        )
        assert "type" in result
        assert "memory" in result
    finally:
        db.close()