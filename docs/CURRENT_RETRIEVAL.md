# Current Retrieval Reference

## Public API Contract

```python
retrieve_memories(db, query: str, limit: int = 5, include_archived: bool = False) -> List[Tuple[Memory, float]]
```

> [!NOTE]
> `include_archived` defaults to `False` to maintain 100% backward compatibility. When `include_archived=True`, archived memories are included in candidate discovery to allow ContextEngine historical evidence evaluation.

> [!NOTE]
> `ContextCandidate.similarity` is retained for backward compatibility, but in the current ContextEngine pipeline it represents the final hybrid retrieval score returned by `retrieve_memories()`.

---

## Candidate Discovery & Fusion Pipeline

```
Query String
  ↓
Single Query Embedding Generation (generate_embedding)
  ↓
Candidate Gathering:
  ├── 1. Semantic Vector Search (pgvector, cosine distance)
  ├── 2. Keyword Text Search (SQL ILIKE across non-stopwords)
  └── 3. Knowledge Graph Expansion (GraphSearch on entities & non-stopword query terms)
  ↓
Candidate Deduplication:
  • Keyed by memory.id in candidate_map
  • Prevents N+1 database queries via bulk fetch for missing memory IDs
  ↓
Multi-Signal Feature Scoring (compute_hybrid_rank_score):
  • Semantic Score (1.0 - distance)       × 0.40 (SEMANTIC_WEIGHT)
  • Keyword Score (term match ratio)      × 0.20 (KEYWORD_WEIGHT)
  • Graph Score (1-hop connected)          × 0.15 (GRAPH_WEIGHT)
  • Importance Score (memory.importance)   × 0.10 (IMPORTANCE_WEIGHT)
  • Recency Score (decay formula)          × 0.06 (RECENCY_WEIGHT)
  • Access Strength (log(access_count))    × 0.04 (ACCESS_WEIGHT)
  • Category Intent (query intent match)   × 0.05 (CATEGORY_WEIGHT)
  • Contradiction Penalty (is_contradicted) - 0.80 (CONTRADICTION_PENALTY)
  ↓
Filtering & Final Ranking:
  • Exclude state == "archived" (unless include_archived=True)
  • Sort by final composite score descending
  • Return top-limit [(Memory, score), ...]
```

---

## Explicit Tuneable Weights (`app/ranking_service.py`)

- `SEMANTIC_WEIGHT = 0.40`
- `KEYWORD_WEIGHT = 0.20`
- `GRAPH_WEIGHT = 0.15`
- `IMPORTANCE_WEIGHT = 0.10`
- `RECENCY_WEIGHT = 0.06`
- `ACCESS_WEIGHT = 0.04`
- `CATEGORY_WEIGHT = 0.05`
- `CONTRADICTION_PENALTY = 0.80`

---

## Historical Retrieval Limitation

> [!WARNING]
> Historical mode can expose a broader archived candidate pool than strictly necessary; future retrieval improvements should make historical candidate discovery more targeted.
