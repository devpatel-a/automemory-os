from sqlalchemy.orm import Session

from app.service import (
    create_memory,
    reinforce_existing_memory,
    contradict_existing_memory,
)
from app.understanding.memory_parser import parse_memory
from app.knowledge.processor import process_knowledge
from app.decision.decision_engine import decide
from app.decision.decision_types import MemoryAction
from app.graph.graph_service import GraphService
from app.semantic.semantic_service import semantic_search


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
        Decision Engine
            ↓
        Memory Engine (Evolution: Store / Reinforce / Contradict / Update)
            ↓
        Knowledge Graph
    """

    def __init__(self, db: Session):
        self.db = db
        self.graph_service = GraphService()

    def process(
        self,
        content: str,
        category: str,
    ):
        # 1. Understanding
        parsed_memory = parse_memory(content)

        # 2. Retrieve Candidates for Knowledge Processing
        candidates = semantic_search(self.db, content, limit=5)

        # 3. Knowledge Engine
        knowledge = process_knowledge(parsed_memory, candidates)

        # 4. Decision Engine
        decision = decide(knowledge)

        # 5. Memory Engine Execution based on Decision
        if decision.action == MemoryAction.REINFORCE and candidates:
            existing_mem = candidates[0][0]
            memory = reinforce_existing_memory(self.db, existing_mem)
        elif decision.action == MemoryAction.ARCHIVE and candidates:
            # Handle contradiction: archive existing memory and create new
            existing_mem = candidates[0][0]
            memory = create_memory(content=content, category=category)
            contradict_existing_memory(self.db, existing_mem, memory.id)
        else:
            memory = create_memory(content=content, category=category)

        # 6. Knowledge Graph
        graph = self.graph_service.process_memory(
            parsed_memory=parsed_memory,
            memory_id=memory.id,
        )

        return {
            "memory": memory,
            "parsed": parsed_memory,
            "knowledge": knowledge,
            "decision": decision,
            "graph": graph,
        }