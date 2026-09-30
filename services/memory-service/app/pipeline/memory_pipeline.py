from sqlalchemy.orm import Session

from app.service import (
    create_memory,
    reinforce_existing_memory,
    contradict_existing_memory,
    update_existing_fact_memory,
    supersede_existing_fact_memory,
    merge_existing_memories,
    calculate_importance,
)
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.semantic.semantic_service import generate_embedding
from app.understanding.memory_parser import parse_memory
from app.knowledge.processor import process_knowledge
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.classifier import is_merge_equivalent
from app.knowledge.contradiction_detector import detect_contradiction
from app.knowledge.knowledge_types import KnowledgeDecision
from app.decision.decision_engine import decide
from app.decision.decision_types import MemoryAction
from app.graph.graph_service import GraphService
from app.semantic.semantic_service import semantic_search


def get_memory_object(item):
    if hasattr(item, "content"):
        return item
    if hasattr(item, "__getitem__"):
        return item[0]
    return item


def is_memory_superseded(db: Session, memory_id: int) -> bool:
    """Check if a memory has already been superseded by another memory in MemoryRelationship."""
    if not memory_id:
        return False
    rel = (
        db.query(MemoryRelationship)
        .filter(
            MemoryRelationship.source_memory_id == memory_id,
            MemoryRelationship.relationship_type == "superseded_by",
        )
        .first()
    )
    return rel is not None


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
        Memory Engine (Evolution: Store / Reinforce / Update / Merge / Contradict)
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
        self.db.expire_all()
        candidates = semantic_search(self.db, content, limit=5)

        # 3. Knowledge Engine
        knowledge = process_knowledge(parsed_memory, candidates)

        # 4. Decision Engine
        decision = decide(knowledge)

        # 5. Memory Engine Execution based on Decision
        if decision.action in (MemoryAction.UPDATE, MemoryAction.ARCHIVE) and candidates:
            target_mem = None
            new_fact = extract_fact(parsed_memory) if parsed_memory else None
            if new_fact:
                norm_ent = new_fact.entity.strip().lower()
                norm_attr = new_fact.attribute.strip().lower()

                # First pass: Prefer active non-superseded candidate as target memory
                for item in candidates:
                    cm = get_memory_object(item)
                    if hasattr(cm, "content") and not getattr(cm, "is_contradicted", False):
                        cm_id = getattr(cm, "id", None)
                        if cm_id and not is_memory_superseded(self.db, cm_id):
                            ef = extract_fact(parse_memory(cm.content))
                            if (
                                ef
                                and ef.entity.strip().lower() == norm_ent
                                and ef.attribute.strip().lower() == norm_attr
                            ):
                                target_mem = cm
                                break

                # Fallback pass if no non-superseded target candidate found
                if not target_mem:
                    for item in candidates:
                        cm = get_memory_object(item)
                        if hasattr(cm, "content") and not getattr(cm, "is_contradicted", False):
                            ef = extract_fact(parse_memory(cm.content))
                            if (
                                ef
                                and ef.entity.strip().lower() == norm_ent
                                and ef.attribute.strip().lower() == norm_attr
                            ):
                                target_mem = cm
                                break

            if target_mem and knowledge.decision == KnowledgeDecision.SUPERSESSION:
                # SUPERSESSION: Create new memory instance, preserving target_mem in DB for historical queries
                embedding = generate_embedding(content)
                memory = Memory(
                    content=content,
                    category=category,
                    importance=calculate_importance(category),
                    embedding=embedding,
                    state="active",
                )
                self.db.add(memory)
                self.db.commit()
                self.db.refresh(memory)
                supersede_existing_fact_memory(self.db, target_mem, memory.id)
            elif target_mem and decision.action == MemoryAction.UPDATE:
                # UPDATE: In-place fact update on target memory
                memory = update_existing_fact_memory(
                    self.db, target_mem, content, category
                )
            elif decision.action == MemoryAction.ARCHIVE:
                contradictory_cand = target_mem or get_memory_object(candidates[0])
                memory = create_memory(content=content, category=category, db=self.db)
                if getattr(contradictory_cand, "id", None) != memory.id:
                    contradict_existing_memory(self.db, contradictory_cand, memory.id)
            else:
                memory = create_memory(content=content, category=category, db=self.db)

        elif decision.action == MemoryAction.MERGE and candidates:
            merge_candidates = []
            for item in candidates:
                cm = get_memory_object(item)
                dist = (
                    item[1]
                    if hasattr(item, "__getitem__") and len(item) > 1
                    else None
                )
                if is_merge_equivalent(parsed_memory, cm, distance=dist):
                    merge_candidates.append(cm)

            if merge_candidates:
                memory = merge_existing_memories(
                    self.db, merge_candidates, content, category
                )
            else:
                memory = create_memory(content=content, category=category, db=self.db)

        elif decision.action == MemoryAction.REINFORCE and candidates:
            existing_mem = get_memory_object(candidates[0])
            memory = reinforce_existing_memory(self.db, existing_mem)

        elif decision.action == MemoryAction.ARCHIVE and candidates:
            contradictory_cand = None
            if parsed_memory:
                for item in candidates:
                    cm = get_memory_object(item)
                    if detect_contradiction(parsed_memory, cm):
                        contradictory_cand = cm
                        break

            memory = create_memory(content=content, category=category, db=self.db)
            if contradictory_cand and getattr(contradictory_cand, "id", None) != memory.id:
                contradict_existing_memory(self.db, contradictory_cand, memory.id)

        else:
            memory = create_memory(content=content, category=category, db=self.db)

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