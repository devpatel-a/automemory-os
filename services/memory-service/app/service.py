from .database import SessionLocal
from .models import Memory


def create_memory(memory_text: str):
    db = SessionLocal()

    try:
        memory = Memory(memory=memory_text)

        db.add(memory)
        db.commit()
        db.refresh(memory)

        return memory

    finally:
        db.close()


def get_memories():
    db = SessionLocal()

    try:
        return db.query(Memory).all()

    finally:
        db.close()