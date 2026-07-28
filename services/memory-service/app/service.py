from .database import SessionLocal
from .models import Memory


def create_memory(content: str, category: str):
    db = SessionLocal()

    try:
        memory = Memory(
            content=content,
            category=category,
        )

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

def update_memory(memory_id: int, memory_text: str):
    db = SessionLocal()

    try:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()

        if memory is None:
            return {"error": "Memory not found."}

        memory.memory = memory_text

        db.commit()
        db.refresh(memory)

        return {
            "message": "Memory updated successfully.",
            "memory": memory
        }

    finally:
        db.close()

def delete_memory(memory_id: int):
    db = SessionLocal()

    try:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()

        if memory is None:
            return {"error": "Memory not found."}

        db.delete(memory)
        db.commit()

        return {
            "message": "Memory deleted successfully."
        }

    finally:
        db.close()