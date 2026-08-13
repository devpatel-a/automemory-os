# Context Engine

## Purpose

The Context Engine selects, scores, diversifies, and assembles the most relevant memories for an incoming user query into an optimized context prompt package for downstream consumption.

---

## Historical Strategy

The initial prototype of the Context Engine used a simplified 3-step strategy:
1. Ignore archived memories (`state == "archived"`)
2. Sort candidates by static importance (`importance`)
3. Select the top-K candidates

---

## Current Implementation

The current Context Engine ([app/context/context_engine.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/context/context_engine.py)) operates as a multi-stage contextual optimization pipeline:

```
Query
  ↓
Query Entity Extraction (extract_query_entities)
  ↓
Hybrid Candidate Retrieval (retrieve_memories)
  ↓
Multi-Signal Context Scoring (Similarity + Entity Match + Category Match + Temporal Match)
  ↓
Candidate Ranking (rank_candidates)
  ↓
Diversity Optimization (diversify_candidates, limit=10)
  ↓
Token Budget Optimization (optimize_token_budget, max_characters=1200)
  ↓
Context Assembly (assemble_context → ContextPackage)
```

### Output Package

`build_context()` returns a structured `ContextPackage` containing:
- Original query text
- Grouped memory strings (`profile`, `preferences`, `habits`, `events`, `other`)
- Character-budget-constrained representation formatted for downstream LLM prompts.

---

## Dependencies

- [app/retrieval_service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/retrieval_service.py)
- `app/context/` modules (`entity_matcher`, `category_matcher`, `temporal_matcher`, `ranker`, `diversity`, `token_budget`, `assembler`)