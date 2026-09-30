"""
Alembic environment. Uses DATABASE_URL via app.config unless an explicit
connection is handed in through config.attributes["connection"] (tests).
"""

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import settings
from app.database import Base
import app.models  # noqa: F401  (register tables)
import app.models_relationship  # noqa: F401
import app.graph.db_models  # noqa: F401
import app.provenance.models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(
        context.config.get_main_option("sqlalchemy.url") or settings.database_url,
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        _run(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
