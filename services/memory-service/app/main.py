from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routes import router
from .startup import validate_runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on configurations guaranteed to break later (missing spaCy
    # model, embedding/vector dimension mismatch, unmigrated database).
    validate_runtime()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(router)


@app.get("/")
def home():
    return {
        "service": "Memory Service",
        "status": "Running"
    }
