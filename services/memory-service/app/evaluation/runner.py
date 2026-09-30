"""
Benchmark runner.

Every scenario runs inside an outer database transaction that is rolled back
afterwards (pipeline commits become SAVEPOINT releases), so running the
benchmark never modifies existing data in the configured database. The
process-shared knowledge graph is reset per scenario.

Usage:
    python -m app.evaluation.runner            # human-readable report
    python -m app.evaluation.runner --json     # machine-readable report
"""

import argparse
import contextlib
import io
import json
from dataclasses import asdict, dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine
from app.evaluation.metrics import (
    mean,
    ndcg_at_k,
    pair_precision_recall,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from app.evaluation.scenarios import EXTRACTION_CASES, SCENARIOS, Scenario
from app.graph.repository import GraphRepository, reset_shared_graph
from app.knowledge.fact_extractor import extract_fact
from app.models import Memory
from app.models_relationship import MemoryRelationship
from app.understanding.memory_parser import parse_memory

DEFAULT_K = 3


@dataclass
class QueryResult:
    query: str
    ranked: list[str]
    precision_at_1: float
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float
    forbidden_selected: list[str]


@dataclass
class ScenarioResult:
    name: str
    queries: list[QueryResult] = field(default_factory=list)
    superseded_predicted: list[tuple[str, str]] = field(default_factory=list)
    contradicted_predicted: list[tuple[str, str]] = field(default_factory=list)
    edge_checks_passed: int = 0
    edge_checks_total: int = 0
    canonical_passed: int = 0
    canonical_total: int = 0
    failures: list[str] = field(default_factory=list)


@contextlib.contextmanager
def isolated_session():
    """Session whose changes (including commits) are rolled back on exit."""
    connection = engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        session.execute(text("DELETE FROM memory_relationships"))
        session.execute(text("DELETE FROM memories"))
        reset_shared_graph()
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()
        reset_shared_graph()


def ranked_contents(package) -> list[str]:
    """Selected memory contents in rank order.

    Uses structured evidence when present; falls back to the category buckets
    so packages from older engines (pre-evidence) can be benchmarked too.
    """
    evidence = getattr(package, "evidence", None)
    if evidence:
        return [e.content for e in evidence]
    return package.profile + package.preferences + package.habits + package.events + package.other


def _lineage_pairs(db, relationship_type: str) -> set[tuple[str, str]]:
    content = {m.id: m.content for m in db.query(Memory).all()}
    rows = db.query(MemoryRelationship).filter(
        MemoryRelationship.relationship_type == relationship_type
    )
    return {
        (content.get(r.source_memory_id), content.get(r.target_memory_id))
        for r in rows
    }


def _contradiction_pairs(db) -> set[tuple[str, str]]:
    memories = db.query(Memory).all()
    content = {m.id: m.content for m in memories}
    return {
        (m.content, content.get(m.contradicted_by_id))
        for m in memories
        if m.is_contradicted
    }


def _live_fact_count(db, fact_key: tuple[str, str, str]) -> int:
    count = 0
    for memory in db.query(Memory).filter(Memory.state != "archived"):
        fact = extract_fact(parse_memory(memory.content))
        if fact and (
            fact.entity.lower(), fact.attribute.lower(), fact.value.lower()
        ) == fact_key:
            count += 1
    return count


def run_scenario(scenario: Scenario, k: int = DEFAULT_K) -> ScenarioResult:
    # Local imports keep module import light for metric-only consumers.
    from app.context.context_engine import ContextEngine
    from app.pipeline.memory_pipeline import MemoryPipeline

    result = ScenarioResult(name=scenario.name)

    with isolated_session() as db, contextlib.redirect_stdout(io.StringIO()):
        pipeline = MemoryPipeline(db)
        for statement, category in scenario.statements:
            pipeline.process(statement, category)
        db.expire_all()

        engine_ = ContextEngine()
        for case in scenario.queries:
            package = engine_.build_context(db, case.query)
            ranked = ranked_contents(package)
            relevant = set(case.relevant)
            forbidden = [c for c in ranked if c in set(case.forbidden)]
            result.queries.append(QueryResult(
                query=case.query,
                ranked=ranked,
                precision_at_1=precision_at_k(ranked, relevant, 1),
                recall_at_k=recall_at_k(ranked, relevant, k),
                reciprocal_rank=reciprocal_rank(ranked, relevant),
                ndcg_at_k=ndcg_at_k(ranked, relevant, k),
                forbidden_selected=forbidden,
            ))
            if forbidden:
                result.failures.append(f"{case.query!r} selected forbidden {forbidden}")

        result.superseded_predicted = sorted(_lineage_pairs(db, "superseded_by"))
        result.contradicted_predicted = sorted(_contradiction_pairs(db))

        graph = GraphRepository().load()
        edges = {(e.source.lower(), e.relationship.lower(), e.target.lower()) for e in graph.edges}
        for edge in scenario.edges_present:
            result.edge_checks_total += 1
            if edge in edges:
                result.edge_checks_passed += 1
            else:
                result.failures.append(f"missing edge {edge}")
        for edge in scenario.edges_absent:
            result.edge_checks_total += 1
            if edge not in edges:
                result.edge_checks_passed += 1
            else:
                result.failures.append(f"unsupported edge {edge}")

        for fact_key in scenario.canonical_facts:
            result.canonical_total += 1
            live = _live_fact_count(db, fact_key)
            if live == 1:
                result.canonical_passed += 1
            else:
                result.failures.append(f"{fact_key} has {live} live memories (expected 1)")

    for label, predicted, expected in (
        ("superseded", result.superseded_predicted, scenario.superseded),
        ("contradicted", result.contradicted_predicted, scenario.contradicted),
    ):
        if set(predicted) != set(expected):
            result.failures.append(f"{label}: predicted {predicted}, expected {list(expected)}")

    return result


def evaluate_extraction() -> dict:
    fact_hits = temporal_hits = 0
    misses = []
    for case in EXTRACTION_CASES:
        fact = extract_fact(parse_memory(case.text))
        got = (fact.entity, fact.attribute, fact.value) if fact else None
        if got == (case.entity, case.attribute, case.value):
            fact_hits += 1
        else:
            misses.append(f"fact {case.text!r}: got {got}")
        if fact and fact.temporal_state == case.temporal_state:
            temporal_hits += 1
        else:
            misses.append(
                f"temporal {case.text!r}: got {fact.temporal_state if fact else None}, "
                f"expected {case.temporal_state}"
            )
    total = float(len(EXTRACTION_CASES))
    return {
        "fact_extraction_accuracy": fact_hits / total,
        "temporal_classification_accuracy": temporal_hits / total,
        "misses": misses,
    }


def run_benchmark(k: int = DEFAULT_K) -> dict:
    scenario_results = [run_scenario(s, k) for s in SCENARIOS]
    queries = [q for r in scenario_results for q in r.queries]

    sup_pred = {(r.name,) + p for r in scenario_results for p in r.superseded_predicted}
    sup_exp = {(s.name,) + p for s in SCENARIOS for p in s.superseded}
    con_pred = {(r.name,) + p for r in scenario_results for p in r.contradicted_predicted}
    con_exp = {(s.name,) + p for s in SCENARIOS for p in s.contradicted}
    sup_p, sup_r = pair_precision_recall(sup_pred, sup_exp)
    con_p, con_r = pair_precision_recall(con_pred, con_exp)

    edge_total = sum(r.edge_checks_total for r in scenario_results)
    canon_total = sum(r.canonical_total for r in scenario_results)

    metrics = {
        "k": k,
        "precision_at_1": mean([q.precision_at_1 for q in queries]),
        f"recall_at_{k}": mean([q.recall_at_k for q in queries]),
        "mrr": mean([q.reciprocal_rank for q in queries]),
        f"ndcg_at_{k}": mean([q.ndcg_at_k for q in queries]),
        "forbidden_selection_rate": mean([1.0 if q.forbidden_selected else 0.0 for q in queries]),
        "supersession_precision": sup_p,
        "supersession_recall": sup_r,
        "contradiction_precision": con_p,
        "contradiction_recall": con_r,
        "graph_edge_accuracy": (
            sum(r.edge_checks_passed for r in scenario_results) / edge_total if edge_total else 1.0
        ),
        "duplicate_suppression_accuracy": (
            sum(r.canonical_passed for r in scenario_results) / canon_total if canon_total else 1.0
        ),
    }
    extraction = evaluate_extraction()
    metrics["fact_extraction_accuracy"] = extraction["fact_extraction_accuracy"]
    metrics["temporal_classification_accuracy"] = extraction["temporal_classification_accuracy"]

    return {
        "metrics": metrics,
        "scenarios": [asdict(r) for r in scenario_results],
        "extraction_misses": extraction["misses"],
    }


def _print_report(report: dict) -> None:
    print("AutoMemory OS benchmark")
    print("=" * 60)
    for name, value in report["metrics"].items():
        print(f"{name:34} {value:.3f}" if isinstance(value, float) else f"{name:34} {value}")
    print()
    for scenario in report["scenarios"]:
        status = "ok" if not scenario["failures"] else "FAIL"
        print(f"[{status}] {scenario['name']}")
        for query in scenario["queries"]:
            print(f"    {query['query']!r:40} RR={query['reciprocal_rank']:.2f} -> {query['ranked']}")
        for failure in scenario["failures"]:
            print(f"    ! {failure}")
    if report["extraction_misses"]:
        print("\nExtraction misses:")
        for miss in report["extraction_misses"]:
            print(f"    - {miss}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-k", type=int, default=DEFAULT_K)
    args = parser.parse_args()
    report = run_benchmark(k=args.k)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
