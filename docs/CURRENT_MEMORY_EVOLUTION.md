# Current Memory Evolution Reference

## Overview & Responsibility Boundaries

Memory Evolution is responsible for memory persistence, state machine transitions, confidence updates, relationship preservation, and memory consolidation ([app/service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/service.py)).

Graph indexing is performed by the Graph System ([app/graph/graph_service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/graph/graph_service.py)) as a downstream stage orchestrated by `MemoryPipeline`.

---

## Architectural Responsibility Flow

```
Memory Evolution Engine (app/service.py)
  ↓
Memory Persistence / State Transition
  ↓
MemoryPipeline Orchestrator (app/pipeline/memory_pipeline.py)
  ↓
Graph Indexing (GraphService().process_memory)
```

---

## Evolution Actions & Safety Rules

### 1. STORE (`create_memory`)
- Creates a new active memory (`state = "active"`).
- Generates 384-dimensional vector embedding.
- Persistence performed in `app/service.py`; entity indexing into the Knowledge Graph is subsequently triggered by `MemoryPipeline`.

### 2. REINFORCE (`reinforce_existing_memory`)
- Triggered on exact duplicate detection.
- Increases importance (`min(1.0, importance + 0.05)`).
- Increments `access_count` by 1.
- Boosts confidence (`min(1.0, confidence + 0.10)`).
- Updates `last_accessed` timestamp.

### 3. UPDATE (`update_existing_fact_memory`)
- Triggered on fact value transitions (`same entity + same attribute + different value`).
- Requires normalized entity + normalized attribute match with different value.
- Updates existing memory content and embedding in-place.
- Keeps `state = "active"` and `is_contradicted = False`.

### 4. MERGE (`merge_existing_memories`)
- Triggered when `is_merge_equivalent()` returns `True`.
- Rejects merge on entity/similarity alone without merge equivalence.
- Merges candidate into canonical memory (`max(importance)`, `max(confidence)`, `sum(access_count)`).
- Transfers relationships from duplicate to canonical memory, preventing duplicate relationship rows.
- Transitions duplicate memory to `state = "archived"`.
- Merged redundant memories keep `is_contradicted = False` and `contradicted_by_id = None`.

### 5. CONTRADICTION / ARCHIVE (`contradict_existing_memory`)
- Triggered when `detect_contradiction()` returns `True`.
- Scans candidates to identify the **exact** contradictory candidate.
- Sets target memory `state = "archived"`, `is_contradicted = True`, `contradicted_by_id = new_memory.id`.
- Stores new replacing memory as `state = "active"`, `is_contradicted = False`.
