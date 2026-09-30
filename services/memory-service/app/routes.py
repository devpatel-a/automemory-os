from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import service
from .database import get_db
from .context_service import build_context
from .context.context_engine import ContextEngine
from .agent_service import MemoryAgent
from .pipeline.memory_pipeline import MemoryPipeline
from .schemas import (
    MemoryCreate,
    MemoryUpdate,
    MemoryResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    MemoryEvidenceResponse,
)
from .provenance.models import Provenance

router = APIRouter()


@router.get(
    "/memory",
    response_model=list[MemoryResponse],
)
def get_memories(
    category: str | None = None,
    min_importance: float | None = None,
    keyword: str | None = None,
):
    return service.get_memories(
        category=category,
        min_importance=min_importance,
        keyword=keyword,
    )


@router.post(
    "/memory",
    response_model=MemoryResponse,
)
def create_memory(
    memory: MemoryCreate,
    db: Session = Depends(get_db),
):
    pipeline = MemoryPipeline(db)
    result = pipeline.process(
        content=memory.content,
        category=memory.category,
        provenance=Provenance(
            source_type=memory.source_type,
            conversation_id=memory.conversation_id,
            message_id=memory.message_id,
            observed_at=memory.observed_at,
        ),
    )
    return result["memory"]


@router.get(
    "/memory/{memory_id}/evidence",
    response_model=MemoryEvidenceResponse,
)
def get_memory_evidence(
    memory_id: int,
    db: Session = Depends(get_db),
):
    """Provenance and lineage for one memory (read-only)."""
    return service.get_memory_evidence(memory_id, db=db)


@router.put(
    "/memory/{memory_id}",
    response_model=MemoryResponse,
)
def update_memory(
    memory_id: int,
    memory: MemoryUpdate,
):
    return service.update_memory(
        memory_id=memory_id,
        content=memory.content,
    )


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: int):
    return service.delete_memory(memory_id)


@router.get(
    "/context",
    response_model=list[MemoryResponse],
)
def get_context(
    query: str | None = None,
    top_k: int = 5,
):
    return build_context(
        query=query,
        top_k=top_k,
    )


@router.post(
    "/agent/query",
    response_model=AgentQueryResponse,
)
def agent_query(
    request: AgentQueryRequest,
    db: Session = Depends(get_db),
):
    agent = MemoryAgent(db)
    return agent.query(
        user_query=request.query,
        top_k=request.top_k,
    )


@router.post(
    "/agent/chat",
)
def agent_chat(
    content: str,
    category: str = "fact",
    db: Session = Depends(get_db),
):
    agent = MemoryAgent(db)
    return agent.chat(
        user_input=content,
        category=category,
    )


@router.post(
    "/pipeline/process",
)
def process_pipeline(
    content: str,
    category: str = "fact",
    source_type: str = "api",
    conversation_id: str | None = None,
    message_id: str | None = None,
    db: Session = Depends(get_db),
):
    pipeline = MemoryPipeline(db)
    result = pipeline.process(
        content=content,
        category=category,
        provenance=Provenance(
            source_type=source_type,
            conversation_id=conversation_id,
            message_id=message_id,
        ),
    )
    return {
        "memory_id": result["memory"].id,
        "content": result["memory"].content,
        "category": result["memory"].category,
        "intent": result["parsed"].intent,
        "action": result["decision"].action.value,
        "reason": result["decision"].reason,
        "knowledge_decision": result["knowledge"].decision.value,
        "reason_codes": result["reason_codes"],
    }