from app.database import SessionLocal
from app.semantic.semantic_service import semantic_search

db = SessionLocal()

results = semantic_search(
    db,
    "I like beverages",
)

for result in results:
    print(result)