from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {
        "service": "Memory Service",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }


@app.get("/memory")
def memory():
    return {
        "memory": "Driver prefers coffee."
    }

@app.get("/info")
def info():
    return {
        "info": "Information about the memory service."
    }