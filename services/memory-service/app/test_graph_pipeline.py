from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline


def test_graph_pipeline_integration():
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        result = pipeline.process(
            "I enjoy cappuccino in Pune.",
            "preference",
        )
        assert "graph" in result
        assert len(result["graph"].nodes) > 0
    finally:
        db.close()