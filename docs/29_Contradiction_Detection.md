# Contradiction Detection

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes contradiction detection concepts. Current contradiction handling rules are documented in [CURRENT_MEMORY_EVOLUTION.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_MEMORY_EVOLUTION.md).

---

## Purpose

The Contradiction Detector identifies direct conflicts between incoming memories and existing active knowledge.

---

## Current Implementation

Contradiction detection is implemented in [app/knowledge/contradiction_detector.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/contradiction_detector.py) via `detect_contradiction(new_parsed, existing_mem)`.

### Core Distinctions

It is critical to distinguish between three related concepts in AutoMemory OS:

1. **UPDATE (Fact Transition)**:
   - Same entity + same attribute + different value (e.g., `"I live in Mumbai."` → `"I live in Pune."`).
   - Represents a normal real-world value transition.
   - Updates the existing memory in-place without setting contradiction flags (`is_contradicted = False`).

2. **CONTRADICTION**:
   - Direct mutual exclusion or explicit negation on profile/attribute facts (e.g., `"I love coffee."` vs `"I hate coffee."` or `"I am vegetarian."` vs `"I eat meat."`).
   - Rejects simple fact transitions (which belong to UPDATE).

3. **Archival & Lineage**:
   - When a CONTRADICTION is executed by `MemoryPipeline`, the engine scans candidates to identify the **exact** contradictory candidate (via `detect_contradiction`).
   - The contradictory candidate is transitioned to `state = "archived"`, `is_contradicted = True`, and `contradicted_by_id = new_memory.id` via `contradict_existing_memory`.
   - The new memory is stored as active (`state = "active"`, `is_contradicted = False`).