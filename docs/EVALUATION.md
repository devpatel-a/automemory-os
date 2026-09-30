# Evaluation Framework

`services/memory-service/app/evaluation/` measures memory quality beyond
"pytest passes".

## Running

```bash
cd services/memory-service
python -m app.evaluation.runner          # readable report
python -m app.evaluation.runner --json   # machine-readable
```

Each scenario runs inside an outer database transaction that is **rolled
back**. Pipeline commits become savepoints, so the benchmark never modifies
existing data. The process-shared graph is reset for each scenario.

## What is measured

| Metric | Source |
| :--- | :--- |
| Precision@1, Recall@k, MRR, nDCG@k | Rank order of `ContextPackage.evidence` against labeled relevant statements |
| Forbidden selection rate | Queries that selected a statement that must not answer them (e.g. a plan for a current question) |
| Supersession precision/recall | Final `superseded_by` lineage pairs vs. labels |
| Contradiction precision/recall | Final `is_contradicted` / `contradicted_by_id` pairs vs. labels |
| Graph edge accuracy | Required edges present, unsupported edges absent |
| Duplicate suppression accuracy | Canonical facts that have exactly one live memory |
| Fact extraction accuracy | `(entity, attribute, value)` on the labeled sentence set |
| Temporal classification accuracy | `temporal_state` on the labeled sentence set |

Scenarios live in `scenarios.py`. Add new scenarios whenever a bug is fixed or
a behavior is specified.

## Regression gate

`app/evaluation/test_benchmark.py` fails if any metric drops below the value
measured when the benchmark was introduced. Raise the thresholds when quality
improves. Never lower one without documenting why.

## Baseline

The same benchmark was run against the untouched v0.8 commit (`0d4eabb`) and
against v0.9. The results are in `docs/ARCHITECTURE_ASSESSMENT.md` §3. The v0.8
run exposed every defect listed there.

## Caveats

- The dataset is small (11 scenarios, 16 queries, 20 extraction sentences) and
  was written alongside the fixes it checks. Treat the numbers as regression
  signals, not as estimates of general quality.
- Ranking weights (`ranking_service.py`, `TEMPORAL_ALIGNMENT_BONUS`) should
  only be tuned against a larger, independently written query set.

## v0.10

- Graph checks read the **persisted** PostgreSQL graph.
- New scenario `plan_fulfilment`. It exposed a ranking flaw (a fulfilled plan
  outranked the past residence for "Where did I live before?"), which was fixed.
  All metrics are at 1.000 on the current benchmark.
- The runner's isolation (outer transaction, rolled back) also covers the graph
  and evidence tables.
