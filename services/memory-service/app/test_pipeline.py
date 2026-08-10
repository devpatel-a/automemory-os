from app.database import SessionLocal

from app.pipeline.memory_pipeline import (
    MemoryPipeline,
)

db = SessionLocal()

pipeline = MemoryPipeline(db)

result = pipeline.process(

    "My favorite drink is coffee.",

    "preference",

)

print(result)