from fastapi import APIRouter

from .schemas import MemoryCreate
from . import service

router = APIRouter()


@router.get("/memory")
def get_memory():
    return service.get_memories()


@router.post("/memory")
def create_memory(memory: MemoryCreate):
    return service.add_memory(memory)


@router.put("/memory/{memory_id}")
def update(memory_id: int, memory: MemoryCreate):
    return service.update_memory(memory_id, memory)


@router.delete("/memory/{memory_id}")
def delete(memory_id: int):
    return service.delete_memory(memory_id)