import pytest

from app.config import load_settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("EMBEDDING_MODEL", "some-model")
    monkeypatch.setenv("CONTEXT_TOKEN_BUDGET", "900")
    settings = load_settings()
    assert settings.database_url == "postgresql://example/db"
    assert settings.embedding_model == "some-model"
    assert settings.context_token_budget == 900


def test_settings_defaults_keep_historical_behavior(monkeypatch):
    for name in ("DATABASE_URL", "EMBEDDING_MODEL", "CONTEXT_TOKEN_BUDGET", "CONTEXT_RETRIEVAL_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings()
    assert "devpatel" not in settings.database_url
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.context_token_budget == 1200
    assert settings.context_retrieval_limit == 10


def test_structural_candidate_limit(monkeypatch):
    monkeypatch.delenv("STRUCTURAL_CANDIDATE_LIMIT", raising=False)
    assert load_settings().structural_candidate_limit == 50
    monkeypatch.setenv("STRUCTURAL_CANDIDATE_LIMIT", "0")   # disables structural discovery
    assert load_settings().structural_candidate_limit == 0
    monkeypatch.setenv("STRUCTURAL_CANDIDATE_LIMIT", "-1")
    with pytest.raises(ValueError):
        load_settings()
