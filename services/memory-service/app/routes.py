from fastapi import APIRouter

from .schemas import MemoryCreate
from . import service

router = APIRouter()


@router.get("/memory")
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


@router.post("/memory")
def create(memory: MemoryCreate):
    return service.create_memory(
        content=memory.content,
        category=memory.category,
    )


@router.put("/memory/{memory_id}")
def update(memory_id: int, memory: MemoryCreate):
    return service.update_memory(
        memory_id=memory_id,
        content=memory.content,
    )


@router.delete("/memory/{memory_id}")
def delete(memory_id: int):
    return service.delete_memory(memory_id)