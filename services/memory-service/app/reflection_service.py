from datetime import UTC, datetime
from sqlalchemy.orm import Session

from app.models import Memory
from app.understanding.memory_parser import parse_memory
from app.knowledge.contradiction_detector import detect_contradiction


class ReflectionEngine:
    """
    Reflection Loop Component for AutoMemory OS.

    Evaluates agent outcomes and user interaction, updating memory access statistics
    (genuine cognitive retrieval) and reporting, without acting on, conflicts between
    the generated response and the memories it used.
    """

    def reflect(
        self,
        db: Session,
        query: str,
        response: str,
        memories_used: list[Memory],
    ) -> dict:
        accessed_ids = []

        # 1. Update access count & recency for memories used in prompt
        for memory in memories_used:
            memory.access_count += 1
            memory.last_accessed = datetime.now(UTC)
            memory.importance = min(memory.importance + 0.02, 1.0)
            accessed_ids.append(memory.id)

        # 2. Inspect whether the generated response conflicts with the memories
        #    it used. This is reported only: generated text is not user
        #    evidence and must never overwrite trusted memory state.
        contradiction_detected = False
        conflicting_ids = []
        parsed_response = parse_memory(response)

        for memory in memories_used:
            if detect_contradiction(parsed_response, memory):
                contradiction_detected = True
                conflicting_ids.append(memory.id)

        db.commit()

        return {
            "accessed_memory_ids": accessed_ids,
            "contradiction_detected": contradiction_detected,
            "conflicting_memory_ids": conflicting_ids,
            "reflection_status": "completed",
        }
