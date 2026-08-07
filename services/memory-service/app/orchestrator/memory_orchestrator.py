from sqlalchemy.orm import Session

from app.semantic.semantic_service import (
    generate_embedding,
    semantic_search,
)

from app.duplicate_service import (
    find_duplicate,
    strengthen_memory,
)

from app.models import Memory


class MemoryOrchestrator:

    def __init__(self, db: Session):
        self.db = db

    def process(
        self,
        content: str,
        category: str,
        importance: float,
    ):

        embedding = generate_embedding(content)

        candidates = semantic_search(
            self.db,
            content,
            limit=5,
        )

        duplicate = find_duplicate(candidates)

        if duplicate:

            strengthen_memory(duplicate)

            return {
                "type": "duplicate",
                "memory": duplicate,
            }

        memory = Memory(
            content=content,
            category=category,
            importance=importance,
            embedding=embedding,
            state="active",
        )

        return {
            "type": "new",
            "memory": memory,
        }