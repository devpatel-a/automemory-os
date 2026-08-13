# Current Context Engine Reference

## Purpose

The Context Engine ([app/context/context_engine.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/context/context_engine.py)) is the evidence-selection and context-quality orchestration layer of AutoMemory OS.

---

## Public API Contract

```python
ContextEngine.build_context(db, query: str) -> ContextPackage
```

---

## Authoritative Evidence Scoring Architecture

Context Evidence Scoring consumes the hybrid retrieval score returned by `retrieve_memories()` and applies context-specific evidence adjustments:

```
Retrieval Score (candidate.similarity / hybrid retrieval score)
  ↓
Context Evidence Adjustments:
  ├── entity_match_bonus           (exact query entity match vs substring overlap)
  ├── fact_attribute_match_bonus   (generic structured KnowledgeFact attribute match)
  └── temporal_intent_bonus        (query temporal expression match)
  ↓
Final Context Evidence Score (evidence_score)
  ↓
Context Re-ranking (rank_candidates by evidence_score descending)
```

> [!NOTE]
> `ContextCandidate.similarity` is retained for backward compatibility, but in the current ContextEngine pipeline it represents the final hybrid retrieval score returned by `retrieve_memories()`.

---

## Formula

$$\text{final\_evidence\_score} = \text{base\_retrieval\_score} + \text{entity\_match\_bonus} + \text{fact\_attribute\_match\_bonus} + \text{temporal\_intent\_bonus}$$

---

## Fact Extraction & Limitations

- **Structured Fact Matching**: Used when `extract_fact()` succeeds in parsing structured entity-attribute-value facts.
- **Fallback Signals**: Unsupported natural-language facts fall back gracefully to semantic, entity, category, and temporal signals.
- **Future Milestone**: Richer natural-language fact understanding belongs to the future Memory Intelligence milestone (`fact_extractor.py` is not expanded in v0.6).

---

## Historical Retrieval & Conflict Resolution

- **Historical Query Detection**: Detects queries requesting past context ("before", "previously", "past", "history", "used to", "earlier").
- **Historical Candidate Retrieval**: When `is_historical_query(query)` is True, `ContextEngine` calls `retrieve_memories(db, query, limit=10, include_archived=True)`.

> [!WARNING]
> Historical mode can expose a broader archived candidate pool than strictly necessary; future retrieval improvements should make historical candidate discovery more targeted.

- **Contradiction Lineage**: Uses `contradicted_by_id`, `is_contradicted`, `state`, and `created_at` (not `last_accessed` access timestamps) to resolve fact domain conflicts.
  - If $A.\text{contradicted\_by\_id} == B.\text{id}$, $B$ is preferred for current queries. $A$ is retained for historical queries.
- **Merge Safety**: Archived merged memories (`is_contradicted = False`, `contradicted_by_id = None`) are excluded when the canonical active memory is present.
- **Near-Duplicate Diversity**: Deduplicates near-duplicate paraphrases using Jaccard token overlap while preserving distinct fact value transitions (e.g., Pune vs Mumbai).
