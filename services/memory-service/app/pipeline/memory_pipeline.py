from sqlalchemy.orm import Session

from app.decision.decision_engine import decide
from app.decision.decision_types import MemoryAction

from app.knowledge.processor import process_knowledge

from app.understanding.memory_parser import parse_memory

from app.service import create_memory


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

        # -----------------------------
        # Understanding Engine
        # -----------------------------

        parsed = parse_memory(content)

        # -----------------------------
        # Knowledge Engine
        # -----------------------------

        knowledge = process_knowledge(
            parsed,
            [],
        )

        # -----------------------------
        # Decision Engine
        # -----------------------------

        decision = decide(
            knowledge,
        )

        # -----------------------------
        # Memory Engine
        # -----------------------------

        if decision.action == MemoryAction.STORE:

            memory = create_memory(
                content,
                category,
            )

        elif decision.action == MemoryAction.REINFORCE:

            memory = create_memory(
                content,
                category,
            )

        elif decision.action == MemoryAction.UPDATE:

            memory = create_memory(
                content,
                category,
            )

        else:

            memory = create_memory(
                content,
                category,
            )

        return {

            "parsed": parsed,

            "knowledge": knowledge,

            "decision": decision,

            "memory": memory,
        }