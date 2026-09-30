"""
Startup validation: refuse to serve in a configuration that is guaranteed to
fail later (missing NLP model, embedding/vector dimension mismatch,
unreachable database or unmigrated schema).
"""

import logging

from sqlalchemy import text

from app.config import settings
from app.models import EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class StartupValidationError(RuntimeError):
    pass


def check_nlp_model() -> None:
    from app.nlp import NLPModelUnavailable, get_nlp

    try:
        get_nlp()
    except NLPModelUnavailable as exc:
        raise StartupValidationError(str(exc)) from exc


def check_embedding_dimension(model_dimension: int, schema_dimension: int = EMBEDDING_DIMENSION) -> None:
    if model_dimension != schema_dimension:
        raise StartupValidationError(
            f"Embedding model '{settings.embedding_model}' produces {model_dimension}-dimensional "
            f"vectors, but memories.embedding is vector({schema_dimension}). Either set "
            f"EMBEDDING_MODEL to a {schema_dimension}-dimensional model, or add a migration that "
            f"changes the column dimension and re-embeds existing memories."
        )


def database_embedding_dimension(connection) -> int | None:
    """Actual vector dimension of memories.embedding in the database (pgvector typmod)."""
    row = connection.execute(text(
        "SELECT a.atttypmod FROM pg_attribute a "
        "JOIN pg_class c ON c.oid = a.attrelid "
        "WHERE c.relname = 'memories' AND a.attname = 'embedding' AND NOT a.attisdropped"
    )).first()
    if row is None or row[0] is None or row[0] < 0:
        return None
    return int(row[0])


def check_database(engine) -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            db_dimension = database_embedding_dimension(connection)
    except Exception as exc:  # connection/driver errors of any kind
        raise StartupValidationError(
            f"Cannot connect to the database configured by DATABASE_URL: {exc}"
        ) from exc

    if db_dimension is None:
        raise StartupValidationError(
            "Table 'memories' (with an 'embedding' vector column) was not found. "
            "Run 'alembic upgrade head' in services/memory-service."
        )
    check_embedding_dimension(db_dimension, EMBEDDING_DIMENSION)


def validate_runtime(engine=None) -> None:
    from app.database import engine as default_engine
    from app.semantic.semantic_service import embedding_dimension

    check_nlp_model()
    check_embedding_dimension(embedding_dimension())
    check_database(engine or default_engine)
    logger.info("Runtime validation passed")
