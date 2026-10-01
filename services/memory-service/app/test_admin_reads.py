"""
Administrative reads must not mutate cognitive state (access_count,
last_accessed, lifecycle state); genuine retrieval may.
"""

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import Memory
from app.service import get_memories
from app.testing_support import reset_database


def seed():
    reset_database()
    db = SessionLocal()
    memory = Memory(content="I live in Pune.", category="profile", state="active", access_count=0)
    db.add(memory)
    db.commit()
    snapshot = (memory.id, memory.access_count, memory.last_accessed, memory.state)
    db.close()
    return snapshot


def reload(memory_id):
    db = SessionLocal()
    try:
        m = db.get(Memory, memory_id)
        return (m.id, m.access_count, m.last_accessed, m.state)
    finally:
        db.close()


def test_get_memory_endpoint_does_not_change_access_state():
    before = seed()
    client = TestClient(app)  # no lifespan: pure route test
    for _ in range(3):
        response = client.get("/memory")
        assert response.status_code == 200
        assert [m["content"] for m in response.json()] == ["I live in Pune."]
    assert reload(before[0]) == before


def test_service_listing_is_read_only_by_default_and_opt_in_records_access():
    before = seed()
    get_memories()
    assert reload(before[0]) == before

    get_memories(record_access=True)
    after = reload(before[0])
    assert after[1] == 1
    assert after[2] > before[2]
