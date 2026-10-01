"""
Database-level integrity: invariants are enforced by PostgreSQL itself,
not only by application code.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import engine
from app.testing_support import reset_database


def _insert_memory(conn, content="I live in Pune.", state="active"):
    return conn.execute(text(
        "INSERT INTO memories (content, category, importance, access_count, state, confidence, is_contradicted) "
        "VALUES (:c, 'profile', 0.9, 0, :s, 1.0, false) RETURNING id"
    ), {"c": content, "s": state}).scalar()


def _insert_rel(conn, src, tgt, kind="superseded_by"):
    conn.execute(text(
        "INSERT INTO memory_relationships (source_memory_id, target_memory_id, relationship_type) "
        "VALUES (:s, :t, :k)"
    ), {"s": src, "t": tgt, "k": kind})


def test_duplicate_relationship_rejected():
    reset_database()
    with engine.connect() as conn:
        a, b = _insert_memory(conn, "A"), _insert_memory(conn, "B")
        _insert_rel(conn, a, b)
        with pytest.raises(IntegrityError, match="uq_memory_relationships_source_target_type"):
            _insert_rel(conn, a, b)
        conn.rollback()


def test_self_relationship_rejected():
    reset_database()
    with engine.connect() as conn:
        a = _insert_memory(conn, "A")
        with pytest.raises(IntegrityError, match="ck_memory_relationships_no_self_link"):
            _insert_rel(conn, a, a)
        conn.rollback()


def test_relationship_requires_existing_memories():
    reset_database()
    with engine.connect() as conn:
        a = _insert_memory(conn, "A")
        with pytest.raises(IntegrityError, match="fk_memory_relationships_target"):
            _insert_rel(conn, a, 999999)
        conn.rollback()


def test_memory_cannot_contradict_itself():
    reset_database()
    with engine.connect() as conn:
        a = _insert_memory(conn, "A")
        with pytest.raises(IntegrityError, match="ck_memories_not_self_contradicted"):
            conn.execute(text("UPDATE memories SET contradicted_by_id = id WHERE id = :a"), {"a": a})
        conn.rollback()


def test_invalid_lifecycle_state_rejected():
    reset_database()
    with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_memories_state"):
            _insert_memory(conn, "A", state="deleted")
        conn.rollback()


def test_contradicted_by_must_reference_a_memory_and_is_cleared_on_delete():
    reset_database()
    with engine.begin() as conn:
        old, new = _insert_memory(conn, "I live in Mumbai."), _insert_memory(conn, "I live in Pune.")
        conn.execute(text("UPDATE memories SET contradicted_by_id = :n WHERE id = :o"), {"n": new, "o": old})
    with engine.connect() as conn:
        with pytest.raises(IntegrityError, match="fk_memories_contradicted_by"):
            conn.execute(text("UPDATE memories SET contradicted_by_id = 999999 WHERE id = :o"), {"o": old})
        conn.rollback()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM memories WHERE id = :n"), {"n": new})
        assert conn.execute(text("SELECT contradicted_by_id FROM memories WHERE id = :o"), {"o": old}).scalar() is None


def test_deleting_a_memory_cascades_its_lineage_rows():
    """Previously DELETE /memory/{id} failed with an FK violation when lineage existed."""
    reset_database()
    with engine.begin() as conn:
        a, b = _insert_memory(conn, "A"), _insert_memory(conn, "B")
        _insert_rel(conn, a, b)
        conn.execute(text("DELETE FROM memories WHERE id = :b"), {"b": b})
        assert conn.execute(text("SELECT count(*) FROM memory_relationships")).scalar() == 0
