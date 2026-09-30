"""
Persistent knowledge graph: restart-safe, shared across workers, transactional,
duplicate-free, and conservative about entity identity.
"""

import os
import subprocess
import sys
import threading

import pytest
from sqlalchemy import func, select

import app.pipeline.memory_pipeline as pipeline_module
from app.database import SessionLocal
from app.graph.db_models import Entity, EntityRelationship
from app.graph.graph_service import GraphService
from app.graph.repository import reset_shared_graph
from app.graph.sql_repository import SqlGraphRepository
from app.pipeline.memory_pipeline import MemoryPipeline
from app.retrieval_service import retrieve_memories
from app.testing_support import reset_database
from app.understanding.memory_parser import parse_memory


def edges(graph):
    return {(e.source, e.relationship, e.target) for e in graph.edges}


@pytest.fixture
def db():
    reset_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def ingest(db, *statements):
    pipeline = MemoryPipeline(db)
    return [pipeline.process(s, "fact")["memory"] for s in statements]


def test_graph_survives_repository_and_process_restart(db):
    ingest(db, "My friend Rahul works at Google.")
    reset_shared_graph()  # the in-process view is gone, as after a restart

    # new session + new repository
    fresh = SessionLocal()
    try:
        graph = SqlGraphRepository(fresh).load()
    finally:
        fresh.close()
    assert {("user", "friend_of", "rahul"), ("rahul", "works_at", "google")} <= edges(graph)

    # a genuinely new Python process
    service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = (
        "from app.database import SessionLocal\n"
        "from app.graph.sql_repository import SqlGraphRepository\n"
        "g = SqlGraphRepository(SessionLocal()).load()\n"
        "print(sorted((e.source, e.relationship, e.target) for e in g.edges))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script], cwd=service_dir, env=dict(os.environ),
        capture_output=True, text=True, timeout=300,
    )
    assert out.returncode == 0, out.stderr
    assert "('rahul', 'works_at', 'google')" in out.stdout


def test_two_service_instances_share_the_graph(db):
    ingest(db, "I live in Ahmedabad.")
    other = SessionLocal()
    try:
        graph = SqlGraphRepository(other).load()
        assert ("user", "lives_in", "ahmedabad") in edges(graph)
        node = next(n for n in graph.nodes if n.id == "ahmedabad")
        assert node.memory_ids
    finally:
        other.close()


def test_rahul_patel_and_rahul_sharma_are_distinct_entities(db):
    friend, patel, sharma = ingest(
        db,
        "My friend Rahul works at Google.",
        "Rahul Patel lives in Delhi.",
        "Rahul Sharma works at BMW.",
    )
    repo = SqlGraphRepository(db)
    ids = {n: repo.resolve(n) for n in ("rahul", "rahul patel", "rahul sharma")}
    assert len(set(ids.values())) == 3

    assert repo.resolve_query_entities("Where does Rahul Sharma work?") == [ids["rahul sharma"]]
    assert repo.resolve_query_entities("Where does Rahul work?") == [ids["rahul"]]
    assert repo.memory_ids_for_query("Where does Rahul Sharma work?") == {sharma.id}
    assert repo.memory_ids_for_query("What does Rahul do?") == {friend.id}


def test_graph_retrieval_does_not_conflate_similar_names(db):
    friend, patel, sharma = ingest(
        db,
        "My friend Rahul works at Google.",
        "Rahul Patel lives in Delhi.",
        "Rahul Sharma works at BMW.",
    )
    graph_hits = SqlGraphRepository(db).memory_ids_for_query("Tell me about Rahul Patel")
    assert graph_hits == {patel.id}
    assert patel.id in {m.id for m, _ in retrieve_memories(db, "Tell me about Rahul Patel", limit=5)}


def test_explicit_alias_resolves_to_its_entity(db):
    (memory,) = ingest(db, "Rahul Patel lives in Delhi.")
    repo = SqlGraphRepository(db)
    patel = repo.resolve("Rahul Patel")
    assert repo.resolve("RP") is None
    repo.add_alias(patel, "RP")
    db.commit()
    assert repo.resolve("rp") == patel
    assert repo.memory_ids_for_query("Where does RP live?") == {memory.id}


def test_no_duplicate_rows_when_a_statement_repeats(db):
    ingest(db, "I live in Pune.")
    count = lambda model: db.execute(select(func.count()).select_from(model)).scalar()
    before = (count(Entity), count(EntityRelationship))
    ingest(db, "I live in Pune.")
    db.expire_all()
    assert (count(Entity), count(EntityRelationship)) == before


def test_graph_writes_roll_back_with_the_evolution(db, monkeypatch):
    ingest(db, "I live in Mumbai.")
    before = SqlGraphRepository(db).load()

    def failing_contradict(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(pipeline_module, "contradict_existing_memory", failing_contradict)
    with pytest.raises(RuntimeError):
        MemoryPipeline(db).process("I live in Zanzibar.", "profile")

    after = SqlGraphRepository(db).load()
    assert {n.id for n in after.nodes} == {n.id for n in before.nodes}
    assert "zanzibar" not in {n.id for n in after.nodes}


def test_concurrent_entity_upserts_create_one_entity(db):
    barrier = threading.Barrier(4)
    results, errors = [], []

    def worker():
        session = SessionLocal()
        try:
            barrier.wait()
            results.append(SqlGraphRepository(session).upsert_entity("Quantum Computing"))
            session.commit()
        except Exception as exc:
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors
    assert len(set(results)) == 1
    db.expire_all()
    assert db.execute(
        select(func.count()).select_from(Entity).where(Entity.normalized_name == "quantum computing")
    ).scalar() == 1


def test_relationships_use_verb_lemmas_not_substrings(db):
    ingest(db, "I stay home because of the rain.")
    graph = SqlGraphRepository(db).load()
    assert not any(rel == "uses" for _, rel, _ in edges(graph))


def test_work_on_is_not_employment(db):
    ingest(db, "I work on my MacBook Air.")
    graph = SqlGraphRepository(db).load()
    assert ("user", "work_on", "macbook air") in edges(graph)
    assert not any(rel == "works_at" for _, rel, _ in edges(graph))


def test_persist_requires_a_session():
    with pytest.raises(RuntimeError):
        GraphService().persist_memory(parse_memory("I like tea."), 1)
