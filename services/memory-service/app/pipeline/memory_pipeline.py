from sqlalchemy.orm import Session

from app.understanding.memory_parser import (
    parse_memory,
)

from app.knowledge.processor import (
    process_knowledge,
)

from app.service import (
    create_memory,
)


class MemoryPipeline:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def process(
        self,
        content: str,
        category: str,
    ):
        """
        Full AutoMemory OS pipeline.
        """

        parsed = parse_memory(content)

        knowledge = process_knowledge(
            parsed,
            [],
        )

        memory = create_memory(
            content,
            category,
        )

        return {

            "parsed": parsed,

            "knowledge": knowledge,

            "memory": memory,
        }