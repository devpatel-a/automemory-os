from sqlalchemy.orm import Session

from app.models import Memory


class MemoryRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def save(
        self,
        memory: Memory,
    ):

        self.db.add(memory)

        self.db.commit()

        self.db.refresh(memory)

        return memory

    def get(
        self,
        memory_id: int,
    ):

        return (
            self.db.query(Memory)
            .filter(
                Memory.id == memory_id
            )
            .first()
        )

    def delete(
        self,
        memory: Memory,
    ):

        self.db.delete(memory)

        self.db.commit()