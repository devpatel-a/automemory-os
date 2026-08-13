# Semantic Duplicate Detection

## Purpose

Prevents redundant storage of semantically equivalent memories.

---

## Current Implementation Workflow

```
New Memory Text
  ↓
Generate Vector Embedding (SentenceTransformer)
  ↓
pgvector Cosine Distance Search (semantic_search)
  ↓
Knowledge Classification & Merge Equivalence (is_merge_equivalent)
  ↓
Decision: REINFORCE / UPDATE / MERGE / NEW
```

- **Exact Duplicate**: Triggers `REINFORCE` (increments access count and importance).
- **Fact Value Transition**: Triggers `UPDATE` (updates existing memory in-place).
- **Semantically Equivalent**: Triggers `MERGE` (consolidates canonical memory and archives redundant duplicate).