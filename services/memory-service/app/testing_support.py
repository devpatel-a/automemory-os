"""
Test-only database helpers.

Destructive operations are refused unless BOTH hold:
1. the database name is an explicit test name: it matches ^[a-z0-9_]+_test$
   (e.g. automemory_os_test; "contest_prod", "latest" or "test_prod" do not);
2. the operator explicitly approved exactly that database for destructive
   tests: AUTOMEMORY_TEST_DATABASE=<database name>.

The guard lives in the destructive helpers themselves (reset_database,
prepare_test_schema), not only in the pytest session hooks, so calling them
from anywhere against a real database fails loudly instead of wiping data.
"""

import os
import re

from sqlalchemy import text
from sqlalchemy.engine import make_url

TEST_DATABASE_PATTERN = re.compile(r"^[a-z0-9_]+_test$")
APPROVAL_ENV = "AUTOMEMORY_TEST_DATABASE"


class UnsafeTestDatabaseError(RuntimeError):
    pass


def is_test_database_name(name: str) -> bool:
    return bool(TEST_DATABASE_PATTERN.match(name or ""))


def assert_test_database(url: str | None = None, approved: str | None = None) -> str:
    """
    Return the database name, or raise unless it is an explicitly approved,
    explicitly named test database. `approved` defaults to $AUTOMEMORY_TEST_DATABASE.
    """
    if url is None:
        from app.database import engine

        url = engine.url.render_as_string(hide_password=True)
    if approved is None:
        approved = os.environ.get(APPROVAL_ENV, "")
    name = make_url(url).database or ""

    if not is_test_database_name(name):
        raise UnsafeTestDatabaseError(
            f"Refusing destructive test operation on database '{name}': test databases "
            f"must be named '<name>_test' (e.g. automemory_os_test)."
        )
    if approved != name:
        raise UnsafeTestDatabaseError(
            f"Refusing destructive test operation on database '{name}': it is not approved. "
            f"Set {APPROVAL_ENV}={name} to confirm this database may be wiped."
        )
    return name


def assert_scratch_test_database_name(name: str) -> str:
    """
    Guard for throwaway databases a test creates itself (CREATE DATABASE fails
    if the name already exists, so an existing database can never be reused).
    """
    if not is_test_database_name(name):
        raise UnsafeTestDatabaseError(f"Scratch database '{name}' must be named '<name>_test'.")
    return name


def reset_database() -> None:
    """Delete all application rows (test databases only) and reset the in-process graph."""
    assert_test_database()

    from app.database import Base, engine
    from app.graph.repository import reset_shared_graph
    import app.models  # noqa: F401  register tables
    import app.models_relationship  # noqa: F401
    import app.graph.db_models  # noqa: F401
    import app.provenance.models  # noqa: F401

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    reset_shared_graph()


def run_migrations(connection=None) -> None:
    """Apply all Alembic migrations (alembic upgrade head)."""
    import os
    from alembic import command
    from alembic.config import Config

    service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config = Config(os.path.join(service_dir, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(service_dir, "alembic"))
    if connection is not None:
        config.attributes["connection"] = connection
    command.upgrade(config, "head")


def prepare_test_schema() -> None:
    """Migrate the (verified) test database to the latest schema."""
    assert_test_database()
    run_migrations()
