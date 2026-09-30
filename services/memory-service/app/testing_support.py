"""
Test-only database helpers.

Destructive operations are refused unless the configured database is clearly a
test database (its name contains "test"). The guard lives in the helper itself,
not only in conftest, so calling it from anywhere against a real database fails
loudly instead of wiping data.
"""

from sqlalchemy import text
from sqlalchemy.engine import make_url

TEST_DATABASE_MARKER = "test"


class UnsafeTestDatabaseError(RuntimeError):
    pass


def assert_test_database(url: str | None = None) -> str:
    """Return the database name, or raise if it is not clearly a test database."""
    if url is None:
        from app.database import engine

        url = engine.url.render_as_string(hide_password=True)
    name = make_url(url).database or ""
    if TEST_DATABASE_MARKER not in name.lower():
        raise UnsafeTestDatabaseError(
            f"Refusing destructive test operation on database '{name}'. Tests delete data: "
            f"point DATABASE_URL at a dedicated database whose name contains "
            f"'{TEST_DATABASE_MARKER}' (e.g. automemory_os_test)."
        )
    return name


def reset_database() -> None:
    """Delete all application rows (test databases only) and reset the in-process graph."""
    assert_test_database()

    from app.database import Base, engine
    from app.graph.repository import reset_shared_graph
    import app.models  # noqa: F401  register tables
    import app.models_relationship  # noqa: F401

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))
    reset_shared_graph()


def prepare_test_schema() -> None:
    """Create the schema on the (verified) test database."""
    assert_test_database()

    from app.database import Base, engine
    import app.models  # noqa: F401
    import app.models_relationship  # noqa: F401

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
