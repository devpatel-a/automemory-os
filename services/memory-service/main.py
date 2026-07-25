from fastapi import FastAPI

app = FastAPI()

memories = []


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
def add_memory():
    memories.append({
        "memory": "Driver prefers coffee."
    })

    return {
        "message": "Memory added successfully."
    }