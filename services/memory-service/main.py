from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {
        "service": "Memory Service",
        "status": "Running",
        "message": "Welcome to AutoMemory OS"
    }