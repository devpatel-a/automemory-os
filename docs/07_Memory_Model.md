# Memory Model

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes the foundational memory data model. Current schema fields and implementation details are documented in [CURRENT_MEMORY_EVOLUTION.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_MEMORY_EVOLUTION.md).

---

## Purpose

Defines the core data schema for persistent memories in AutoMemory OS ([app/models.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/models.py)).

---

## Current Schema Fields

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `Integer` (Primary Key) | Unique memory identifier. |
| `content` | `String` / `Text` | The textual content of the memory. |
| `category` | `String` | Categorization tag (`profile`, `preference`, `habit`, `event`). |
| `importance` | `Float` | Dynamic importance rating $[0.0, 1.0]$. |
| `confidence` | `Float` | Fact belief confidence $[0.0, 1.0]$. |
| `access_count` | `Integer` | Counter tracking memory access frequency. |
| `state` | `String` | Lifecycle state (`"active"`, `"weak"`, `"archived"`). |
| `is_contradicted` | `Boolean` | Flag indicating whether this memory was superseded by a contradiction. |
| `contradicted_by_id` | `Integer` (Foreign Key) | Foreign key pointing to the replacing active memory ID. |
| `embedding` | `Vector(384)` | 384-dimensional dense pgvector embedding. |
| `created_at` | `DateTime(timezone=True)` | Creation timestamp (UTC). |
| `last_accessed` | `DateTime(timezone=True)` | Last access/reinforcement timestamp (UTC). |