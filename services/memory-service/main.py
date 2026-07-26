from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

memories = []

# Creates a schema for the memory data using Pydantic's BaseModel. This schema will be used to validate incoming requests to the /memory endpoint.
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
# "FastAPI, expect the request body to match the Memory model."
def add_memory(memory: Memory):
    # converts the validated object into a normal Python dictionary before storing it.
    memories.append(memory.dict())

    return {
        "message": "Memory added successfully.",
        "memory": memory
    }