# Current Context Engine Reference

## Overview

The Context Engine ([app/context/context_engine.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/context/context_engine.py)) operates as an evidence-selection and context-quality layer.

---

## 9-Stage Pipeline Architecture

1. **Query Understanding & Entity Extraction** (`query_understanding.py`):
   - Extracts query entities using spaCy NLP.
2. **Historical Intent Detection** (`historical_detector.py`):
   - Detects past intent keywords ("previously", "used to", "history").
3. **Candidate Candidate Retrieval** (`retrieval_service.py`):
   - Fetches up to 10 candidates using `retrieve_memories(db, query, limit=10, include_archived=historical)`.
4. **Evidence Evaluation** (`evidence_evaluator.py`):
   - Computes deterministic `evidence_score` combining base hybrid retrieval score, exact entity match bonus, generic fact attribute match bonus, category match bonus, and temporal match bonus.
5. **Conflict Resolution & Lineage Filtering** (`conflict_resolver.py`):
   - Resolves contradicting memories (`contradicted_by_id`) and excludes archived merged duplicates.
6. **Context Re-ranking** (`ranker.py`):
   - Orders resolved candidates by `evidence_score` descending.
7. **Diversity Optimization** (`diversity.py`):
   - Deduplicates near-duplicate candidates using Jaccard token overlap threshold (`0.75`).
8. **Token Budget Optimization** (`budget.py`):
   - Fits candidates into prompt character limit (`1200` characters).
9. **Context Assembly** (`assembly.py`):
   - Formats final structured `ContextPackage`.
