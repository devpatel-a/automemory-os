from sqlalchemy.orm import Session

from app.service import create_memory

from app.understanding.memory_parser import (
    parse_memory,
)

from app.knowledge.processor import (
    process_knowledge,
)

from app.decision.decision_engine import (
    decide,
)

from app.graph.graph_service import (
    GraphService,
)


class MemoryPipeline:
    """
    AutoMemory OS Memory Pipeline

    Flow

        User Input
            ↓
        Understanding
            ↓
        Knowledge
            ↓
        Decision
            ↓
        Memory Engine
            ↓
        Knowledge Graph
    """

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.graph_service = GraphService()

    def process(
        self,
        content: str,
        category: str,
    ):
        # ---------------------------------
        # Understanding
        # ---------------------------------

        parsed_memory = parse_memory(
            content,
        )

        # ---------------------------------
        # Knowledge
        # ---------------------------------

        knowledge = process_knowledge(
            parsed_memory,
            [],
        )

        # ---------------------------------
        # Decision
        # ---------------------------------

        decision = decide(
            knowledge,
        )

        # ---------------------------------
        # Memory Engine
        # ---------------------------------

        memory = create_memory(
            content=content,
            category=category,
        )

        # ---------------------------------
        # Knowledge Graph
        # ---------------------------------

        graph = self.graph_service.process_memory(
            parsed_memory=parsed_memory,
            memory_id=memory.id,
        )

        # ---------------------------------
        # Pipeline Result
        # ---------------------------------

        return {
            "memory": memory,
            "parsed": parsed_memory,
            "knowledge": knowledge,
            "decision": decision,
            "graph": graph,
        }