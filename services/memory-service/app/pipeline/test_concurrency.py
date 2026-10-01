"""
Concurrent evolution: invariants hold under simultaneous requests, enforced
with PostgreSQL row locks, advisory locks and unique constraints (not
Python-only checks).
"""

import threading

from sqlalchemy import text

from app import lineage
from app.database import SessionLocal, engine
from app.models import Memory
from app.pipeline.memory_pipeline import MemoryPipeline
from app.testing_support import reset_database


def run_concurrently(*statements, category="profile"):
    barrier = threading.Barrier(len(statements))
    errors = []

    def worker(statement):
        session = SessionLocal()
        try:
            pipeline = MemoryPipeline(session)
            barrier.wait()
            pipeline.process(statement, category)
        except Exception as exc:  # surfaced to the test below
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(s,)) for s in statements]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    assert not errors, errors


def live_memories():
    session = SessionLocal()
    try:
        return session.query(Memory).filter(Memory.state != "archived").all()
    finally:
        session.close()


def all_memories():
    session = SessionLocal()
    try:
        return session.query(Memory).order_by(Memory.id).all()
    finally:
        session.close()


def test_same_memory_inserted_concurrently_yields_one_record():
    reset_database()
    run_concurrently(*["I live in Pune."] * 5)
    rows = [m for m in all_memories() if m.content == "I live in Pune."]
    assert len(rows) == 1
    # created once, reinforced four times: no lost updates between the
    # create_memory exact-match path and the pipeline reinforcement path
    assert rows[0].access_count == 4


def test_same_fact_contradicted_concurrently_stays_consistent():
    reset_database()
    session = SessionLocal()
    MemoryPipeline(session).process("I live in Mumbai.", "profile")
    session.close()

    run_concurrently("I live in Pune.", "I live in Delhi.")

    memories = all_memories()
    live_residence = [m for m in memories if m.state != "archived"]
    assert len(live_residence) == 1, [(m.content, m.state) for m in memories]

    by_id = {m.id: m for m in memories}
    contradicted = [m for m in memories if m.is_contradicted]
    assert len(contradicted) == 2
    for memory in contradicted:
        assert memory.state == "archived"
        assert memory.contradicted_by_id in by_id
        assert memory.contradicted_by_id != memory.id
    # Each claim is contradicted by a different, later claim (a chain, not a fork).
    assert len({m.contradicted_by_id for m in contradicted}) == 2


def test_same_memory_reasserted_concurrently():
    reset_database()
    session = SessionLocal()
    pipeline = MemoryPipeline(session)
    pipeline.process("I live in Mumbai.", "profile")
    pipeline.process("I live in Pune.", "profile")
    session.close()

    run_concurrently("I live in Mumbai.", "I live in Mumbai.")

    memories = all_memories()
    mumbai = [m for m in memories if m.content == "I live in Mumbai."]
    pune = [m for m in memories if m.content == "I live in Pune."]
    assert len(mumbai) == 1 and mumbai[0].state != "archived" and not mumbai[0].is_contradicted
    assert len(pune) == 1 and pune[0].is_contradicted and pune[0].contradicted_by_id == mumbai[0].id


def test_same_relationship_created_concurrently_is_stored_once():
    reset_database()
    session = SessionLocal()
    a = Memory(content="A", category="fact", state="active")
    b = Memory(content="B", category="fact", state="active")
    session.add_all([a, b])
    session.commit()
    a_id, b_id = a.id, b.id
    session.close()

    barrier = threading.Barrier(4)
    errors = []

    def worker():
        s = SessionLocal()
        try:
            barrier.wait()
            lineage.link(s, a_id, b_id, lineage.SUPERSEDED_BY)
            s.commit()
        except Exception as exc:
            errors.append(exc)
        finally:
            s.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM memory_relationships")).scalar() == 1


def test_exact_match_reinforcement_waits_for_concurrent_row_update():
    """Deterministic lost-update check: while one transaction holds the row
    lock and has incremented access_count, create_memory() for the same text
    must wait and then build on the committed value (not a stale read)."""
    import time

    from app.service import create_memory, lock_memory

    reset_database()
    setup = SessionLocal()
    memory = Memory(content="I live in Pune.", category="profile", state="active", access_count=0)
    setup.add(memory)
    setup.commit()
    memory_id = memory.id
    setup.close()

    holder = SessionLocal()
    locked = lock_memory(holder, holder.get(Memory, memory_id))
    locked.access_count += 1
    holder.flush()  # uncommitted increment, row lock held

    errors = []

    def concurrent_reinforce():
        session = SessionLocal()
        try:
            create_memory("I live in Pune.", "profile", db=session)
        except Exception as exc:
            errors.append(exc)
        finally:
            session.close()

    worker = threading.Thread(target=concurrent_reinforce)
    worker.start()
    time.sleep(1.0)  # let the worker reach the row lock
    holder.commit()
    holder.close()
    worker.join(timeout=60)

    assert not errors, errors
    check = SessionLocal()
    try:
        assert check.get(Memory, memory_id).access_count == 2
    finally:
        check.close()
