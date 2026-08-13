# Memory Lifecycle

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes the memory lifecycle state machine. Current state machine transitions are documented in [CURRENT_MEMORY_EVOLUTION.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_MEMORY_EVOLUTION.md).

---

## Purpose

Defines the lifecycle state machine for stored memories.

---

## Current Lifecycle States

1. **`active`**: Default active state. Accessible for hybrid retrieval and context construction.
2. **`weak`**: State assigned to low-importance or decayed memories.
3. **`archived`**: Inactive state assigned to memories that have been merged or contradicted. Excluded from normal hybrid retrieval.

---

## State Transitions

- **Creation**: New memories are initialized as `state = "active"`.
- **UPDATE**: Modifies existing memory content in-place while keeping `state = "active"`.
- **MERGE**: Canonical memory remains `active`; redundant duplicate memory is transitioned to `state = "archived"`.
- **CONTRADICTION**: Replacing memory is created as `active`; contradictory target memory is transitioned to `state = "archived"` with `is_contradicted = True`.