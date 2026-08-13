# Memory Merging

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes memory merging concepts. The current MERGE implementation is documented in [CURRENT_MEMORY_EVOLUTION.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_MEMORY_EVOLUTION.md).

---

## Purpose

Memory Merging consolidates semantically equivalent memories into a single canonical memory, preserving history and relationships while eliminating duplicate records.

---

## Historical Implementation

Earlier documentation described merging as simple reinforcement (incrementing access count and importance on an existing memory).

---

## Current Implementation

Memory Merging is fully implemented in the Memory Engine evolution layer ([app/service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/service.py) `merge_existing_memories(db, candidates, new_content, category)`).

### Workflow & Safety Rules

1. **Merge Equivalence Requirement**: MERGE operates **only** on candidates validated by `is_merge_equivalent()`. Broad top-k position or shared entity alone is insufficient.
2. **Canonical State Preservation**:
   - Importance: `max(canonical.importance, duplicate.importance)`
   - Confidence: `min(max(candidate_confidences) + 0.05, 1.0)`
   - Access Count: `sum(access_count) + 1`
   - Created At: `min(created_at)` (preserves earliest timestamp)
   - Last Accessed: `datetime.now(UTC)`
3. **Redundant Memory Archival**: The duplicate memory is transitioned to `state = "archived"`.
4. **Contradiction Flag Protection**: Merged redundant memories are **not** contradictions. Their `is_contradicted` flag remains `False` and `contradicted_by_id` remains `None`.
5. **Relationship Transfer & Deduplication**: Relationships targeting or sourced from the duplicate memory are re-linked to the canonical memory. Duplicate relationships (`(source, target, type)`) are automatically avoided.