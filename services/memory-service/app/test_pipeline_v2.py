from app.database import SessionLocal

from app.pipeline.memory_pipeline import (
    MemoryPipeline,
)

db = SessionLocal()

pipeline = MemoryPipeline(db)

result = pipeline.process(

    "Coffee is my favorite drink.",

    "preference",

)

print(result["decision"])

print()

print(result["memory"])