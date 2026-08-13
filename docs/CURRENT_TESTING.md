# Current Testing Reference

## Overview

The repository currently contains 74 tests across 36 test modules in `services/memory-service/app/`.

---

## Test Execution Status

- **Tests Present**: 74
- **Tests Executed**: 74
- **Latest Verified Result**: 74 passed, 0 failed, 0 skipped (Pass Rate: 100%).

---

## Test Execution Command

```bash
PYTHONPATH=services/memory-service .venv/bin/python -m pytest services/memory-service -q
```

---

## Protected Behaviors by Test Module

| Test Module | Key Behaviors Protected |
| :--- | :--- |
| **`test_context_optimization.py`** | Generic fact relevance; contradiction lineage (`contradicted_by_id`); historical query retrieval; merge safety; near-duplicate Jaccard diversity; multi-candidate token budget truncation (>1200 chars); negative regression tests A-J (no candidates[0] blind selection, no category/importance/recency dominance, gracefully handles empty candidate set). |
| **`test_intelligent_retrieval.py`** | Multi-source candidate deduplication across Semantic, Keyword, and Graph sources; single query embedding generation; active replacement outranking contradicted memories; old high-similarity memory outranking weak recent memory; importance bonus; access strength; robust graph term discovery; ContextEngine integration; signature compatibility `[(Memory, score), ...]`. |
| **`test_correctness_pass.py`** | Process-level shared graph state across `GraphService` instances; residence and workplace UPDATE transitions; unsafe update prevention; MERGE relationship safety without duplicate relationship records; MERGE state preservation; hybrid retrieval source integration; shared entity moderate similarity non-merge test. |
| **`test_evolution.py`** | Memory evolution state machine transitions (`create_memory`, `reinforce_existing_memory`, `update_existing_fact_memory`, `merge_existing_memories`, `contradict_existing_memory`). |
| **`test_contradiction.py`** | Contradiction detection rules, lineage linking (`contradicted_by_id`), and archival safety. |
| **`test_graph_repository.py` & `test_graph.py`** | In-memory graph node/edge storage, graph search indexing, and thread-safe process sharing. |
| **`test_context.py`** | ContextEngine multi-stage context building and token budget optimization. |