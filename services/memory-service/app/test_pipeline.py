from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline


def test_memory_pipeline_process():
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        result = pipeline.process(
            content="I love coffee in Pune.",
            category="preference",
        )
        assert result["memory"] is not None
        assert result["parsed"] is not None
        assert result["knowledge"] is not None
        assert result["decision"] is not None
        assert result["graph"] is not None
    finally:
        db.close()