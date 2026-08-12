from datetime import UTC, datetime
from sqlalchemy.orm import Session

from app.models import Memory
from app.understanding.memory_parser import parse_memory
from app.knowledge.contradiction_detector import detect_contradiction


class ReflectionEngine:
    """
    Reflection Loop Component for AutoMemory OS.

    Evaluates agent outcomes and user interaction, updating memory access statistics,
    reinforcing recalled memories, and detecting newly surfaced contradictions post-response.
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

        # 2. Parse response to inspect if new facts contradict existing memories
        contradiction_detected = False
        parsed_response = parse_memory(response)

        for memory in memories_used:
            if detect_contradiction(parsed_response, memory):
                memory.is_contradicted = True
                memory.confidence = max(memory.confidence - 0.20, 0.0)
                contradiction_detected = True

        db.commit()

        return {
            "accessed_memory_ids": accessed_ids,
            "contradiction_detected": contradiction_detected,
            "reflection_status": "completed",
        }
