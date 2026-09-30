import pytest

import app.nlp as nlp_module
from app.database import engine
from app.models import EMBEDDING_DIMENSION
from app.nlp import NLPModelUnavailable, get_nlp
from app.semantic.semantic_service import embedding_dimension, generate_embedding
from app.startup import (
    StartupValidationError,
    check_database,
    check_embedding_dimension,
    check_nlp_model,
    database_embedding_dimension,
    validate_runtime,
)


def test_pinned_spacy_model_is_installed():
    """The dependency set must provide the configured spaCy model."""
    import en_core_web_sm  # noqa: F401  (installed from requirements.txt)

    check_nlp_model()
    assert get_nlp().meta["name"] == "core_web_sm"


def test_missing_spacy_model_fails_with_actionable_error(monkeypatch):
    def missing(_name):
        raise OSError("[E050] Can't find model")

    get_nlp.cache_clear()
    monkeypatch.setattr(nlp_module.spacy, "load", missing)
    try:
        with pytest.raises(NLPModelUnavailable, match="never downloads models at runtime"):
            get_nlp()
        with pytest.raises(StartupValidationError):
            check_nlp_model()
    finally:
        get_nlp.cache_clear()


def test_embedding_dimension_matches_schema():
    assert EMBEDDING_DIMENSION == 384
    assert embedding_dimension() == 384
    check_embedding_dimension(384)
    assert len(generate_embedding("hello")) == 384


def test_wrong_embedding_dimension_fails_clearly():
    with pytest.raises(StartupValidationError, match="768-dimensional.*vector\\(384\\)"):
        check_embedding_dimension(768)


def test_database_column_dimension_is_validated():
    with engine.connect() as connection:
        assert database_embedding_dimension(connection) == EMBEDDING_DIMENSION
    check_database(engine)


def test_full_runtime_validation_passes():
    validate_runtime()
