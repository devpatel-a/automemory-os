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