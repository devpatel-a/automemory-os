# Memory Pipeline

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes Memory Pipeline concepts. The authoritative current data flow is documented in [CURRENT_DATA_FLOW.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_DATA_FLOW.md).

---

## Purpose

The Memory Pipeline ([app/pipeline/memory_pipeline.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/pipeline/memory_pipeline.py)) is the primary orchestration entry point of AutoMemory OS.

---

## Current Architecture Flow

```
Input Content & Category
  ↓
1. Understanding Engine (parse_memory)
  ↓
2. Candidate Retrieval (semantic_search, limit=5)
  ↓
3. Knowledge Engine (KnowledgeProcessor().process)
  ↓
4. Decision Engine (DecisionEngine().evaluate)
  ↓
5. Memory Engine Evolution (create_memory / reinforce_existing_memory / update_existing_fact_memory / merge_existing_memories / contradict_existing_memory)
  ↓
6. Knowledge Graph Processing (GraphService().process_memory)
```

---

## Actions Executed per Decision

- **STORE**: Creates a new active memory and indexes entities into Knowledge Graph.
- **REINFORCE**: Boosts importance, access count, confidence, and last_accessed on target memory.
- **UPDATE**: Updates existing memory content, embedding, and timestamp in-place (`update_existing_fact_memory`).
- **MERGE**: Merges candidate into canonical memory, transfers relationships, archives duplicate with `is_contradicted = False` (`merge_existing_memories`).
- **ARCHIVE / CONTRADICTION**: Identifies exact contradictory candidate, sets `state = "archived"`, `is_contradicted = True`, `contradicted_by_id = new_memory.id` (`contradict_existing_memory`), and stores new active memory (`create_memory`).
- **RELATED**: Creates new active memory and registers a `related_to` relationship in `memory_relationships`.