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
)

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
    )
    return result["memory"]


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
    db: Session = Depends(get_db),
):
    pipeline = MemoryPipeline(db)
    result = pipeline.process(
        content=content,
        category=category,
    )
    return {
        "memory_id": result["memory"].id,
        "content": result["memory"].content,
        "category": result["memory"].category,
        "intent": result["parsed"].intent,
        "action": result["decision"].action.value,
        "reason": result["decision"].reason,
    }