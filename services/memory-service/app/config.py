"""
Typed, environment-driven settings.

Every value can be overridden through an environment variable; defaults keep
the historical local-development behavior. The default DATABASE_URL carries no
user name: libpq falls back to the operating-system user.
"""

import os
from dataclasses import dataclass


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str
    embedding_model: str
    spacy_model: str
    context_retrieval_limit: int
    context_token_budget: int


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://localhost/automemory_os"),
        embedding_model=os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        spacy_model=os.environ.get("SPACY_MODEL", "en_core_web_sm"),
        context_retrieval_limit=_int_env("CONTEXT_RETRIEVAL_LIMIT", 10),
        # Approximate budget in characters (see app/context/token_budget.py)
        context_token_budget=_int_env("CONTEXT_TOKEN_BUDGET", 1200),
    )


settings = load_settings()
