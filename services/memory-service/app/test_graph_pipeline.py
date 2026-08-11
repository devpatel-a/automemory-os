from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline

db = SessionLocal()

pipeline = MemoryPipeline(db)

result = pipeline.process(
    "I enjoy cappuccino in Pune.",
    "preference",
)

print("=== Graph Nodes ===")
for node in result["graph"].nodes:
    print(node)

print("\n=== Graph Edges ===")
for edge in result["graph"].edges:
    print(edge)