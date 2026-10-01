"""
Lexical matching on whole words, never substrings.

    "car" matches "car" / "cars", never "career", "scary" or "carpool".

- Candidate generation: PostgreSQL full-text search (english configuration,
  GIN index ix_memories_content_fts), see lexical_candidate_ids().
- Scoring: deterministic word-token overlap with light plural folding,
  see lexical_score().
"""

import re

from sqlalchemy import func, literal_column, or_

STOP_WORDS = {
    "the", "is", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "my", "i", "me", "do", "you", "what", "where", "how",
}

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _fold(token: str) -> str:
    """Light, deterministic plural/possessive folding (cars -> car, city's -> city)."""
    if token.endswith("'s"):
        token = token[:-2]
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokens(text: str) -> list[str]:
    return [_fold(t) for t in _WORD.findall((text or "").lower())]


def query_terms(query: str) -> list[str]:
    """Content terms of a query (stop words removed; falls back to all words)."""
    words = [t for t in tokens(query) if len(t) > 1]
    content = [t for t in words if t not in STOP_WORDS]
    return content or words


def lexical_score(content: str, query: str) -> float:
    """
    Normalized lexical relevance in [0, 1] on whole-word tokens.

    1.0 when the query's words appear contiguously in the content; otherwise
    the fraction of query terms present, with a single-term hit in a
    multi-term query treated as weak (0.15 x ratio).
    """
    content_tokens = tokens(content)
    query_tokens = tokens(query)
    if not content_tokens or not query_tokens:
        return 0.0

    n = len(query_tokens)
    if any(content_tokens[i:i + n] == query_tokens for i in range(len(content_tokens) - n + 1)):
        return 1.0

    terms = query_terms(query)
    if not terms:
        return 0.0
    present = set(content_tokens)
    matched = sum(1 for t in terms if t in present)
    ratio = matched / float(len(terms))
    if len(terms) > 1 and matched == 1:
        return 0.15 * ratio
    return ratio


def fts_document(column):
    """to_tsvector('english', <column>): the expression indexed by ix_memories_content_fts."""
    return func.to_tsvector(literal_column("'english'"), column)


def fts_match_any(column, terms: list[str]):
    """Full-text predicate matching any of the terms."""
    document = fts_document(column)
    return or_(*[
        document.op("@@")(func.plainto_tsquery(literal_column("'english'"), term))
        for term in terms
    ])
