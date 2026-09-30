"""
Structural query understanding.

    "What city do I live in?"       -> entity=user, attribute=residence, temporal_intent=CURRENT
    "Where did I live before?"      -> entity=user, attribute=residence, temporal_intent=HISTORICAL
    "Where am I planning to move?"  -> entity=user, attribute=residence, temporal_intent=FUTURE

Reuses the deterministic fact extractor for entity/attribute and the shared
temporal cue baseline for temporal intent. No LLM calls.
"""

from app.context.context_models import QueryIntent
from app.knowledge.fact_extractor import extract_fact
from app.knowledge.temporal_cues import (
    FUTURE_QUERY_CUES,
    HISTORICAL_QUERY_CUES,
    contains_cue,
)
from app.understanding.memory_parser import parse_memory

CURRENT = "CURRENT"
HISTORICAL = "HISTORICAL"
FUTURE = "FUTURE"

# Attributes the extractor emits when it could not identify a real attribute.
_UNINFORMATIVE_ATTRIBUTES = {"general", "be", "do"}


def detect_temporal_intent(query: str) -> str:
    """HISTORICAL takes precedence over FUTURE, matching the v0.8 context behavior."""
    if contains_cue(query, HISTORICAL_QUERY_CUES):
        return HISTORICAL
    if contains_cue(query, FUTURE_QUERY_CUES):
        return FUTURE
    return CURRENT


def analyze_query(query: str) -> QueryIntent:
    if not query or not query.strip():
        return QueryIntent()

    fact = extract_fact(parse_memory(query))
    entity = attribute = None
    if fact is not None:
        entity = fact.entity
        if fact.attribute and fact.attribute.lower() not in _UNINFORMATIVE_ATTRIBUTES:
            attribute = fact.attribute

    return QueryIntent(
        entity=entity,
        attribute=attribute,
        temporal_intent=detect_temporal_intent(query),
    )
