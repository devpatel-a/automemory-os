from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

memories = []


class Memory(BaseModel):
    memory: str


@app.get("/")
def home():
    return {
        "service": "Memory Service",
        "status": "Running"
    }


@app.get("/memory")
def get_memories():
    return memories


@app.post("/memory")
def add_memory(memory: Memory):
    memories.append(memory.model_dump())

    return {
        "message": "Memory added successfully.",
        "memory": memory
    }

@app.put("/memory/{memory_id}")
def update_memory(memory_id: int, memory: Memory):
    if memory_id >= len(memories):
        return {
            "error": "Memory not found."
        }

    memories[memory_id] = memory.model_dump()

    return {
        "message": "Memory updated successfully.",
        "memory": memories[memory_id]
    }


@app.delete("/memory/{memory_id}")
def delete_memory(memory_id: int):
    if memory_id >= len(memories):
        return {
            "error": "Memory not found."
        }

    deleted = memories.pop(memory_id)

    return {
        "message": "Memory deleted successfully.",
        "deleted": deleted
    }