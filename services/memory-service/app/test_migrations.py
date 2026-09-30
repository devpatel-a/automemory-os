"""
Migration tests on throwaway databases (names contain 'test').

- fresh database -> upgrade head -> schema matches the ORM metadata
- downgrade base -> upgrade head round trip
- a legacy v0.9 database created by create_all(), with anomalous data, upgrades
  without losing memories
"""

import uuid
import warnings

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from app.database import Base, engine as app_engine
from app.testing_support import assert_test_database, run_migrations
import app.models  # noqa: F401
import app.models_relationship  # noqa: F401
import app.graph.db_models  # noqa: F401
import app.provenance.models  # noqa: F401


@pytest.fixture
def scratch_engine():
    """A brand-new empty database, dropped afterwards."""
    name = f"automemory_migration_test_{uuid.uuid4().hex[:8]}"
    assert_test_database(f"postgresql://x/{name}")
    admin = create_engine(app_engine.url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    except Exception as exc:  # no CREATEDB privilege in this environment
        pytest.skip(f"cannot create scratch database: {exc}")
    scratch = create_engine(app_engine.url.set(database=name))
    try:
        yield scratch
    finally:
        scratch.dispose()
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _alembic_config(connection):
    import os
    from alembic.config import Config

    service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = Config(os.path.join(service_dir, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(service_dir, "alembic"))
    config.attributes["connection"] = connection
    return config


def _schema_diff(connection):
    with warnings.catch_warnings():
        # Alembic cannot reflect-compare expression indexes (full-text); ignore that warning.
        warnings.simplefilter("ignore")
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    ignored_indexes = {"ix_memories_content_fts"}
    return [
        d for d in diff
        if not (d[0] in ("add_index", "remove_index") and d[1].name in ignored_indexes)
    ]


def test_fresh_database_upgrade_matches_models(scratch_engine):
    with scratch_engine.begin() as conn:
        run_migrations(conn)
    with scratch_engine.connect() as conn:
        assert _schema_diff(conn) == []
        indexes = {row[0] for row in conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'memories'"
        ))}
    assert {"ix_memories_content_fts", "ix_memories_state"} <= indexes


def test_downgrade_and_upgrade_round_trip(scratch_engine):
    with scratch_engine.begin() as conn:
        command.upgrade(_alembic_config(conn), "head")
    with scratch_engine.begin() as conn:
        command.downgrade(_alembic_config(conn), "base")
    with scratch_engine.connect() as conn:
        tables = {row[0] for row in conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))}
    assert "memories" not in tables
    with scratch_engine.begin() as conn:
        command.upgrade(_alembic_config(conn), "head")
    with scratch_engine.connect() as conn:
        assert _schema_diff(conn) == []


LEGACY_V09_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE memories (
    id SERIAL PRIMARY KEY, content TEXT NOT NULL, category VARCHAR(50) NOT NULL,
    importance DOUBLE PRECISION NOT NULL, embedding vector(384),
    access_count INTEGER NOT NULL, state VARCHAR(20) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL, contradicted_by_id INTEGER,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    last_accessed TIMESTAMPTZ DEFAULT now() NOT NULL,
    is_contradicted BOOLEAN NOT NULL
);
CREATE TABLE memory_relationships (
    id SERIAL PRIMARY KEY,
    source_memory_id INTEGER NOT NULL REFERENCES memories(id),
    target_memory_id INTEGER NOT NULL REFERENCES memories(id),
    relationship_type VARCHAR NOT NULL
);
CREATE INDEX ix_memory_relationships_id ON memory_relationships (id);
"""


def test_legacy_create_all_database_upgrades_without_data_loss(scratch_engine):
    with scratch_engine.begin() as conn:
        for statement in LEGACY_V09_DDL.strip().split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.execute(text(
            "INSERT INTO memories (content, category, importance, access_count, state, confidence, is_contradicted) "
            "VALUES ('I live in Mumbai.', 'profile', 0.9, 0, 'active', 1.0, false), "
            "       ('I moved to Pune.', 'profile', 0.9, 0, 'active', 1.0, false), "
            "       ('Odd legacy row.', 'fact', 0.4, 0, 'active', 1.0, false)"
        ))
        conn.execute(text(
            "INSERT INTO memory_relationships (source_memory_id, target_memory_id, relationship_type) "
            "VALUES (1, 2, 'superseded_by'), (1, 2, 'superseded_by'), (3, 3, 'related')"
        ))

    with scratch_engine.begin() as conn:
        run_migrations(conn)

    with scratch_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM memories")).scalar() == 3
        rels = conn.execute(text(
            "SELECT source_memory_id, target_memory_id, relationship_type FROM memory_relationships ORDER BY id"
        )).all()
        # exact duplicate collapsed; the legacy self-link is kept (constraint left NOT VALID)
        assert [tuple(r) for r in rels] == [(1, 2, "superseded_by"), (3, 3, "related")]
        validated = conn.execute(text(
            "SELECT convalidated FROM pg_constraint WHERE conname = 'ck_memory_relationships_no_self_link'"
        )).scalar()
        assert validated is False
        # provenance backfill: one honest 'legacy' row per memory, nothing fabricated
        legacy = conn.execute(text(
            "SELECT e.source_type, e.observed_at = m.created_at, e.raw_text, e.extraction_method, e.message_id "
            "FROM memory_evidence e JOIN memories m ON m.id = e.memory_id"
        )).all()
        assert [tuple(r) for r in legacy] == [("legacy", True, None, None, None)] * 3
