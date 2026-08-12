from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline

db = SessionLocal()

pipeline = MemoryPipeline(db)

result = pipeline.process(
    content="I love coffee in Pune.",
    category="preference",
)

print("\n========== PIPELINE RESULT ==========\n")

print("Memory")
print(result["memory"])

print("\nParsed Memory")
print(result["parsed"])

print("\nKnowledge")
print(result["knowledge"])

print("\nDecision")
print(result["decision"])

print("\nGraph")
print(result["graph"])

print("\n========== SUCCESS ==========\n")