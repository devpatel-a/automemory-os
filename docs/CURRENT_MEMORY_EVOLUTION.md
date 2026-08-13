# Current Memory Evolution Reference

## Purpose

The Memory Evolution Engine ([app/service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/service.py)) executes state transitions on stored user memories in response to Knowledge Engine decisions.

---

## Single-Fact Contract & Temporal Scope

The current `KnowledgeFact` representation represents one structured fact at a time. Compound sentences containing multiple temporal facts (e.g. `"I lived in Mumbai before moving to Pune."`) are not yet decomposed into independent structured facts. The current extractor produces a single primary fact with coarse temporal information.

---

## Fact-Driven Evolution Actions

1. **`STORE`**:
   - Persists new memory object in PostgreSQL database.
   - Inserts vector embedding (`Vector(384)`).

2. **`REINFORCE`**:
   - Increments `access_count` on existing exact duplicate memory.
   - Updates `last_accessed` timestamp.

3. **`UPDATE` (Strict Fact Value Transition)**:
   - **Pre-condition**: Incoming memory and existing memory share `same entity` + `same attribute` with a **different value** (e.g. `user/residence/Mumbai` $\rightarrow$ `user/residence/Pune`).
   - Updates content, embedding, category, and timestamps of target memory in-place.
   - Preserves `is_contradicted = False` and `contradicted_by_id = None`.

4. **`MERGE` (Canonical Consolidation)**:
   - **Pre-condition**: Incoming memory and existing memory express equivalent facts (`same entity` + `same attribute` + `same value` match).
   - Creates/updates canonical active memory.
   - Transfers existing relationships from merged duplicates to canonical memory without creating duplicate relationship records.
   - Archives redundant merged duplicate memories setting `state = "archived"`, `is_contradicted = False`, `contradicted_by_id = None`.

5. **`CONTRADICTION` (Target Lineage Archival)**:
   - **Pre-condition**: Direct conflict identified on comparable fact domain (`same entity` + `same attribute` + `different value`).
   - Creates new active memory (`state = "active"`, `is_contradicted = False`).
   - Archives specifically contradicted target memory setting `state = "archived"`, `is_contradicted = True`, `contradicted_by_id = new_memory.id`.

6. **Unrelated Attributes**:
   - Memories with unrelated attributes (e.g. `user/location/Pune` vs `user/preference/espresso`) must **never** UPDATE or MERGE.
