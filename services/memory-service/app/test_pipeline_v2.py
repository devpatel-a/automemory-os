from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline


def test_memory_pipeline_v2():
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        result = pipeline.process(
            "Coffee is my favorite drink.",
            "preference",
        )
        assert result["decision"] is not None
        assert result["memory"] is not None
    finally:
        db.close()