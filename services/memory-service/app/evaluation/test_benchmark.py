"""
Evaluation framework tests: metric correctness and a benchmark regression gate.

The gate thresholds are the measured values at the time the benchmark was
introduced (see docs/EVALUATION.md). Raise them when quality improves; never
lower them without documenting why.
"""

import math

from app.evaluation.metrics import (
    ndcg_at_k,
    pair_precision_recall,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.evaluation.runner import run_benchmark


def test_ranking_metrics():
    ranked = ["a", "b", "c"]
    assert precision_at_k(ranked, {"b"}, 1) == 0.0
    assert precision_at_k(ranked, {"a", "c"}, 2) == 0.5
    assert recall_at_k(ranked, {"a", "z"}, 3) == 0.5
    assert reciprocal_rank(ranked, {"c"}) == 1.0 / 3
    assert reciprocal_rank(ranked, {"z"}) == 0.0
    assert ndcg_at_k(ranked, {"a"}, 3) == 1.0
    assert math.isclose(ndcg_at_k(ranked, {"b"}, 3), 1.0 / math.log2(3))


def test_pair_precision_recall():
    assert pair_precision_recall({(1, 2)}, {(1, 2), (3, 4)}) == (1.0, 0.5)
    assert pair_precision_recall({(1, 2), (5, 6)}, {(1, 2)}) == (0.5, 1.0)
    assert pair_precision_recall(set(), set()) == (1.0, 1.0)


GATE = {
    "precision_at_1": 1.0,
    "mrr": 1.0,
    "recall_at_3": 1.0,
    "supersession_precision": 1.0,
    "supersession_recall": 1.0,
    "contradiction_precision": 1.0,
    "contradiction_recall": 1.0,
    "graph_edge_accuracy": 1.0,
    "duplicate_suppression_accuracy": 1.0,
    "temporal_classification_accuracy": 1.0,
    "fact_extraction_accuracy": 1.0,
}


def test_benchmark_regression_gate():
    report = run_benchmark(k=3)
    metrics = report["metrics"]
    assert metrics["forbidden_selection_rate"] == 0.0, report["scenarios"]
    below = {
        name: (metrics[name], floor)
        for name, floor in GATE.items()
        if metrics[name] < floor
    }
    failures = [f for s in report["scenarios"] for f in s["failures"]]
    assert not below, (below, failures, report["extraction_misses"])
