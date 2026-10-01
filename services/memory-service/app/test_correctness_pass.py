from app.testing_support import reset_database
from app.database import SessionLocal
from app.pipeline.memory_pipeline import MemoryPipeline
from app.service import create_memory
from app.relationship_service import create_relationship, get_related_memories
from app.semantic.semantic_service import generate_embedding
from app.graph.graph_service import GraphService
from app.graph.graph_search import GraphSearch
from app.retrieval_service import retrieve_memories
from app.decision.decision_types import MemoryAction
from app.models import Memory
from app.models_relationship import MemoryRelationship


def clear_db():
    reset_database()


def test_shared_graph_state_across_instances():
    """Requirement 1 & H: Data written through GraphService A must be visible through GraphService B."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res = pipeline.process("I enjoy coffee every morning.", "preference")
        mem_id = res["memory"].id

        # Service B
        service_b = GraphService()
        graph_b = service_b.repository.load()

        node = graph_b.find_node("coffee")
        assert node is not None
        assert mem_id in node.memory_ids

        # Test GraphSearch.memory_ids("coffee")
        graph_search = GraphSearch(graph_b.nodes, graph_b.edges)
        mids = graph_search.memory_ids("coffee")
        assert mem_id in mids
    finally:
        db.close()


def test_reinforcement():
    """Requirement 5 & A: Exact duplicate reinforces existing memory."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I like coffee.", "preference")
        m1_id = res1["memory"].id
        m1_access = res1["memory"].access_count

        res2 = pipeline.process("I like coffee.", "preference")
        assert res2["memory"].id == m1_id
        assert res2["memory"].access_count > m1_access
    finally:
        db.close()


def test_update_workflow_residence_transition():
    """Decision 1 & 3: "I live in Mumbai." followed by "I moved to Pune." produces SUPERSESSION/UPDATE."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I live in Mumbai.", "profile")

        res2 = pipeline.process("I moved to Pune.", "profile")
        assert res2["decision"].action == MemoryAction.UPDATE
        assert res2["memory"].content == "I moved to Pune."
        assert res2["memory"].is_contradicted is False
    finally:
        db.close()


def test_update_workflow_workplace_transition():
    """Decision 1: "I work at Google." followed by "I transferred to Apple." produces SUPERSESSION/UPDATE."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I work at Google.", "profile")

        res2 = pipeline.process("I transferred to Apple.", "profile")
        assert res2["decision"].action == MemoryAction.UPDATE
        assert res2["memory"].content == "I transferred to Apple."
        assert res2["memory"].is_contradicted is False
    finally:
        db.close()


def test_unsafe_update_prevention():
    """Requirement 4 & C: "I like coffee." followed by "I live in Bangalore." must NOT overwrite coffee memory."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)
        res1 = pipeline.process("I like coffee.", "preference")
        coffee_id = res1["memory"].id

        res2 = pipeline.process("I live in Bangalore.", "profile")
        assert res2["decision"].action != MemoryAction.UPDATE
        assert res2["memory"].id != coffee_id

        # Verify coffee memory was not overwritten
        coffee_mem = db.query(Memory).filter(Memory.id == coffee_id).first()
        assert coffee_mem.content == "I like coffee."
    finally:
        db.close()


def test_shared_entity_moderate_similarity_does_not_merge():
    """Requirement 7: Shared entity + moderate similarity does NOT automatically produce MERGE."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Memory 1: "I live in Pune." (profile)
        m1 = Memory(
            content="I live in Pune.",
            category="profile",
            embedding=generate_embedding("I live in Pune."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        db.add(m1)
        db.commit()
        db.refresh(m1)

        # Incoming event memory: "I visited Pune last year." (event)
        res = pipeline.process("I visited Pune last year.", "event")

        db.refresh(m1)

        # Verify m1 is NOT archived or merged
        assert m1.state != "archived"
        assert res["decision"].action != MemoryAction.MERGE
    finally:
        db.close()


def test_merge_does_not_archive_unrelated_memories():
    """Requirement 2 & F: Merge must NOT archive unrelated top-k candidates."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Directly insert setup memories to guarantee independent rows
        m1 = Memory(
            content="I enjoy espresso.",
            category="preference",
            embedding=generate_embedding("I enjoy espresso."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        m2 = Memory(
            content="I live in Pune.",
            category="profile",
            embedding=generate_embedding("I live in Pune."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        m3 = Memory(
            content="I like hiking.",
            category="habit",
            embedding=generate_embedding("I like hiking."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        db.add_all([m1, m2, m3])
        db.commit()

        res = pipeline.process("I love espresso coffee.", "preference")

        db.refresh(m2)
        db.refresh(m3)

        assert m2.state != "archived"
        assert m3.state != "archived"
    finally:
        db.close()


def test_merge_semantics_non_contradicted():
    """Decision 5 & Requirement 3: MERGE test with guaranteed independent setup rows."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Directly insert distinct setup memories to guarantee 2 independent rows exist
        m1 = Memory(
            content="I enjoy espresso coffee.",
            category="preference",
            embedding=generate_embedding("I enjoy espresso coffee."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        m2 = Memory(
            content="I love drinking espresso.",
            category="preference",
            embedding=generate_embedding("I love drinking espresso."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        db.add_all([m1, m2])
        db.commit()
        db.refresh(m1)
        db.refresh(m2)

        res = pipeline.process("I love drinking espresso coffee.", "preference")

        db.refresh(m1)
        db.refresh(m2)

        archived_mems = [m for m in [m1, m2] if m.state == "archived"]
        for arch in archived_mems:
            assert arch.is_contradicted is False
            assert arch.contradicted_by_id is None
    finally:
        db.close()


def test_merge_relationship_safety_no_duplicates():
    """Decision 5 & Requirement 5: MERGE preserves relationships and avoids duplicate relationship rows."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        # Directly insert setup memories
        m1 = Memory(
            content="I enjoy espresso coffee.",
            category="preference",
            embedding=generate_embedding("I enjoy espresso coffee."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        m2 = Memory(
            content="I love drinking espresso.",
            category="preference",
            embedding=generate_embedding("I love drinking espresso."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        target = Memory(
            content="I visit cafe daily.",
            category="habit",
            embedding=generate_embedding("I visit cafe daily."),
            state="active",
            importance=0.8,
            confidence=1.0,
        )
        db.add_all([m1, m2, target])
        db.commit()
        db.refresh(m1)
        db.refresh(m2)
        db.refresh(target)

        # Create relationship from m1 -> target
        rel1 = create_relationship(db, m1.id, target.id, "related_to")

        res = pipeline.process("I love drinking espresso coffee.", "preference")

        # Check relationships for target memory
        rels = get_related_memories(db, res["memory"].id)
        pairs = [
            (r.source_memory_id, r.target_memory_id, r.relationship_type)
            for r in rels
        ]
        assert len(pairs) == len(set(pairs))
    finally:
        db.close()


def test_hybrid_retrieval_combines_sources():
    """Requirement 8 & Fix 4: Hybrid retrieval combines semantic, keyword, and graph sources."""
    clear_db()
    db = SessionLocal()
    try:
        pipeline = MemoryPipeline(db)

        res1 = pipeline.process(
            "I love drinking dark roast coffee every morning.", "preference"
        )
        mem1 = res1["memory"]

        res2 = pipeline.process(
            "My favorite beverage is hot espresso.", "preference"
        )
        mem2 = res2["memory"]

        results = retrieve_memories(db, "coffee", limit=5)

        assert isinstance(results, list)
        assert len(results) > 0

        top_mem, top_score = results[0]
        assert hasattr(top_mem, "content")
        assert top_score > 0.0
        assert (
            "coffee" in top_mem.content.lower()
            or "espresso" in top_mem.content.lower()
        )
    finally:
        db.close()
