from datetime import UTC, datetime
import math

# Explicit tuneable weights for feature ranking
SEMANTIC_WEIGHT = 0.40
KEYWORD_WEIGHT = 0.20
GRAPH_WEIGHT = 0.15
IMPORTANCE_WEIGHT = 0.10
RECENCY_WEIGHT = 0.06
ACCESS_WEIGHT = 0.04
CATEGORY_WEIGHT = 0.05
CONTRADICTION_PENALTY = 0.80

from app.knowledge.temporal_cues import contains_cue
from app.lexical import STOP_WORDS, lexical_score  # noqa: F401  (STOP_WORDS re-exported)


def normalize_similarity(distance: float | None) -> float:
    """Normalize vector distance to similarity score in range [0, 1]."""
    if distance is None:
        return 0.5
    return max(0.0, min(1.0, 1.0 - float(distance)))


def calculate_keyword_score(content: str, query: str) -> float:
    """
    Calculate normalized keyword relevance score [0, 1] on whole words.
    Distinguishes exact/multi-term matches from weak single-word overlap.
    """
    return lexical_score(content, query)


def calculate_recency_score(last_accessed: datetime | None, created_at: datetime | None) -> float:
    """Calculate normalized recency bonus [0, 1] using controlled exponential decay."""
    ref_time = last_accessed or created_at
    if ref_time is None:
        return 0.5

    now = datetime.now(UTC)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=UTC)

    delta = (now - ref_time).total_seconds()
    days = max(0.0, delta / 86400.0)

    # Controlled decay: 1 day -> 0.9, 7 days -> 0.58, 30 days -> 0.25
    return 1.0 / (1.0 + (days * 0.1))


def calculate_access_score(access_count: int) -> float:
    """Calculate weak access strength score [0, 1] using logarithmic scaling."""
    if access_count <= 0:
        return 0.0
    return min(1.0, math.log1p(access_count) * 0.3)


def infer_query_category(query: str) -> str | None:
    """Infer intended memory category from query keywords."""
    q = query.lower()
    # Linguistic cues only (no domain values such as drinks or foods).
    if contains_cue(q, ["preference", "preferences", "prefer", "prefers", "like", "likes", "favorite", "favorites", "enjoy", "enjoys", "love", "loves"]):
        return "preference"
    if contains_cue(q, ["where", "live", "lives", "work", "works", "name", "age", "profile", "born", "residence", "home"]):
        return "profile"
    if contains_cue(q, ["happened", "recently", "event", "events", "visited", "yesterday", "last", "went"]):
        return "event"
    if contains_cue(q, ["habit", "habits", "daily", "usually", "every", "always", "routine", "routines"]):
        return "habit"
    return None


def calculate_score(memory, distance):
    """Legacy backward-compatible score function."""
    similarity = normalize_similarity(distance)

    score = (
        similarity * 0.50
        + (getattr(memory, "importance", 0.5) or 0.5) * 0.25
        + min((getattr(memory, "access_count", 0) or 0) / 10.0, 1.0) * 0.15
    )

    return score


def compute_hybrid_signals(
    memory,
    semantic_distance: float | None,
    graph_connected: bool,
    query: str,
) -> dict[str, float | None]:
    """Independently measurable retrieval signals, each in [0, 1] (None = not measured)."""
    cat_intent = infer_query_category(query)
    return {
        "semantic": normalize_similarity(semantic_distance) if semantic_distance is not None else None,
        "lexical": calculate_keyword_score(memory.content, query),
        "graph": 1.0 if graph_connected else 0.0,
        "importance": float(getattr(memory, "importance", 0.5) or 0.5),
        "recency": calculate_recency_score(getattr(memory, "last_accessed", None), getattr(memory, "created_at", None)),
        "access": calculate_access_score(getattr(memory, "access_count", 0) or 0),
        "category": 1.0 if (cat_intent and getattr(memory, "category", None) == cat_intent) else 0.0,
    }


def weighted_hybrid_score(signals: dict[str, float | None], is_contradicted: bool = False) -> float:
    """Weighted combination of retrieval signals minus the contradiction penalty."""
    score = (
        SEMANTIC_WEIGHT * (signals["semantic"] or 0.0)
        + KEYWORD_WEIGHT * signals["lexical"]
        + GRAPH_WEIGHT * signals["graph"]
        + IMPORTANCE_WEIGHT * signals["importance"]
        + RECENCY_WEIGHT * signals["recency"]
        + ACCESS_WEIGHT * signals["access"]
        + CATEGORY_WEIGHT * signals["category"]
    )
    if is_contradicted:
        score -= CONTRADICTION_PENALTY
    return max(0.0, score)


def compute_hybrid_rank_score(
    memory,
    semantic_distance: float | None,
    keyword_matched: bool,
    graph_connected: bool,
    query: str,
) -> float:
    """
    Compute final relevance score combining all signals:
    Semantic + Keyword + Graph + Importance + Recency + Access + Category - Contradiction Penalty
    """
    signals = compute_hybrid_signals(memory, semantic_distance, graph_connected, query)
    return weighted_hybrid_score(signals, bool(getattr(memory, "is_contradicted", False)))
