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

from app.decision.decision_types import (
    MemoryAction,
)

from app.graph.graph_service import (
    GraphService,
)


class MemoryPipeline:
    """
    AutoMemory OS Memory Pipeline

    Flow:
        User Input
            ↓
        Understanding Engine
            ↓
        Knowledge Engine
            ↓
        Knowledge Graph
            ↓
        Decision Engine
            ↓
        Memory Engine
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
        # 1. Understanding Engine
        # ---------------------------------

        parsed_memory = parse_memory(
            content,
        )

        # ---------------------------------
        # 2. Knowledge Engine
        # ---------------------------------

        knowledge = process_knowledge(
            parsed_memory,
            [],
        )

        # ---------------------------------
        # 3. Knowledge Graph
        # ---------------------------------

        graph = self.graph_service.process_memory(
            parsed_memory,
        )

        # ---------------------------------
        # 4. Decision Engine
        # ---------------------------------

        decision = decide(
            knowledge,
        )

        # ---------------------------------
        # 5. Memory Engine
        # ---------------------------------

        if decision.action == MemoryAction.STORE:

            memory = create_memory(
                content=content,
                category=category,
            )

        elif decision.action == MemoryAction.REINFORCE:

            memory = create_memory(
                content=content,
                category=category,
            )

        elif decision.action == MemoryAction.UPDATE:

            memory = create_memory(
                content=content,
                category=category,
            )

        elif decision.action == MemoryAction.ARCHIVE:

            memory = create_memory(
                content=content,
                category=category,
            )

        else:

            memory = create_memory(
                content=content,
                category=category,
            )

        # ---------------------------------
        # Return Complete Pipeline Result
        # ---------------------------------

        return {
            "parsed": parsed_memory,
            "knowledge": knowledge,
            "graph": graph,
            "decision": decision,
            "memory": memory,
        }