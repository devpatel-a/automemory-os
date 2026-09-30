from app.testing_support import reset_database
"""
Query-aware, lineage-aware context selection and structured evidence.
"""

from sqlalchemy import text

from app.database import SessionLocal, engine
from app.graph.repository import reset_shared_graph
from app.pipeline.memory_pipeline import MemoryPipeline
from app.context.context_engine import ContextEngine
from app.context.query_intent import analyze_query


def clear_db():
    reset_database()


def ingest(db, statements, category="profile"):
    pipeline = MemoryPipeline(db)
    for statement in statements:
        pipeline.process(statement, category)


def selected(package):
    return [e.content for e in package.evidence]


TIMELINE = [
    "I lived in Delhi.",
    "I live in Mumbai.",
    "I moved to Pune.",
    "I will move to Bangalore next month.",
]


def test_analyze_query_structure():
    current = analyze_query("What city do I live in?")
    assert (current.entity, current.attribute, current.temporal_intent) == ("user", "residence", "CURRENT")
    historical = analyze_query("Where did I live before?")
    assert (historical.attribute, historical.temporal_intent) == ("residence", "HISTORICAL")
    future = analyze_query("Where am I planning to move?")
    assert (future.attribute, future.temporal_intent) == ("residence", "FUTURE")


def test_current_query_never_answered_by_future_plan():
    """Regression: 'Where do I live?' used to return only the Bangalore plan."""
    clear_db()
    db = SessionLocal()
    try:
        ingest(db, TIMELINE)
        package = ContextEngine().build_context(db, "Where do I live?")
        assert selected(package)[0] == "I moved to Pune."
        assert "I will move to Bangalore next month." not in selected(package)
    finally:
        db.close()


def test_superseded_lineage_marks_memory_historical():
    clear_db()
    db = SessionLocal()
    try:
        ingest(db, TIMELINE)
        package = ContextEngine().build_context(db, "Where did I live before?")
        states = {e.content: e.temporal_state for e in package.evidence}
        assert states["I live in Mumbai."] == "HISTORICAL"
        assert states["I lived in Delhi."] == "HISTORICAL"
        assert states["I moved to Pune."] == "CURRENT"
        # Historical evidence ranks above the current fact.
        order = selected(package)
        assert order.index("I live in Mumbai.") < order.index("I moved to Pune.")
    finally:
        db.close()


def test_future_query_prefers_plan():
    clear_db()
    db = SessionLocal()
    try:
        ingest(db, TIMELINE)
        package = ContextEngine().build_context(db, "Where will I move?")
        assert selected(package)[0] == "I will move to Bangalore next month."
        assert package.evidence[0].temporal_state == "FUTURE"
    finally:
        db.close()


def test_multi_valued_facts_are_not_collapsed():
    clear_db()
    db = SessionLocal()
    try:
        ingest(db, ["I like coffee.", "I like tea."], category="preference")
        package = ContextEngine().build_context(db, "What do I like?")
        assert set(package.preferences) == {"I like coffee.", "I like tea."}
    finally:
        db.close()


def test_package_carries_structured_evidence():
    clear_db()
    db = SessionLocal()
    try:
        ingest(db, ["I live in Mumbai.", "I moved to Pune."])
        package = ContextEngine().build_context(db, "What city do I live in?")

        assert package.intent is not None
        assert package.intent.attribute == "residence"
        assert package.intent.temporal_intent == "CURRENT"

        top = package.evidence[0]
        assert top.memory_id is not None
        assert (top.entity, top.attribute, top.value) == ("user", "residence", "Pune")
        assert top.temporal_state == "CURRENT"
        assert top.lifecycle_state == "active"
        assert top.confidence is not None
        assert top.reasons, "evidence must explain why it was selected"
        # Backward-compatible text buckets are still populated.
        assert "I moved to Pune." in package.profile
    finally:
        db.close()
