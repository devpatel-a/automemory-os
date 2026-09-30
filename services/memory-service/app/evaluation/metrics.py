"""
Retrieval / classification metrics (binary relevance). Pure functions, no I/O.
"""

import math
from typing import Hashable, Sequence


def precision_at_k(ranked: Sequence[Hashable], relevant: set, k: int) -> float:
    if k <= 0:
        return 0.0
    top = list(ranked)[:k]
    if not top:
        return 0.0
    return sum(1 for item in top if item in relevant) / float(len(top))


def recall_at_k(ranked: Sequence[Hashable], relevant: set, k: int) -> float:
    if not relevant:
        return 1.0
    top = list(ranked)[:k]
    return sum(1 for item in top if item in relevant) / float(len(relevant))


def reciprocal_rank(ranked: Sequence[Hashable], relevant: set) -> float:
    for index, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked: Sequence[Hashable], relevant: set, k: int) -> float:
    if not relevant:
        return 1.0
    dcg = sum(
        1.0 / math.log2(index + 1)
        for index, item in enumerate(list(ranked)[:k], start=1)
        if item in relevant
    )
    ideal = sum(1.0 / math.log2(index + 1) for index in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def pair_precision_recall(predicted: set, expected: set) -> tuple[float, float]:
    """Precision/recall over sets of predicted vs expected pairs (e.g. contradiction links)."""
    precision = len(predicted & expected) / float(len(predicted)) if predicted else 1.0
    recall = len(predicted & expected) / float(len(expected)) if expected else 1.0
    return precision, recall
