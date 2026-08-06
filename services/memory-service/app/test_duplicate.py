from app.database import SessionLocal
from app.semantic.semantic_service import semantic_search
from app.duplicate_service import find_duplicate

db = SessionLocal()

results = semantic_search(
    db,
    "Coffee is my favorite beverage",
)

duplicate = find_duplicate(results)

if duplicate:
    print("Duplicate Found:")
    print(duplicate.content)
else:
    print("No duplicate.")