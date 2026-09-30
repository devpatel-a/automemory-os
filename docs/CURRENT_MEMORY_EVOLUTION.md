# Current Memory Evolution Reference

## Overview

Memory Evolution governs how new natural language facts interact with existing memories stored in PostgreSQL.

---

## v0.8 Knowledge Decision Matrix

| Incoming Fact State | Existing Memory State | Value Match | Transition Evidence | Knowledge Decision | Memory Action | Resulting Database State |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Same Entity + Attribute | Same Entity + Attribute | Same Value | N/A | `REINFORCEMENT` / `MERGE` | `REINFORCE` / `MERGE` | Importance/confidence boosted; equivalent memories merged into canonical record. |
| `CURRENT` | `HISTORICAL` | Different Value | N/A | `SUPERSESSION` | `UPDATE` | New active memory created; existing memory preserved as `state = "active"`, linked via `MemoryRelationship("superseded_by")`. |
| `CURRENT` / Transition | `CURRENT` | Different Value | Explicit (`"moved to"`, `"transferred to"`) | `SUPERSESSION` | `UPDATE` | New active memory created; existing memory preserved as `state = "active"`, linked via `MemoryRelationship("superseded_by")`. |
| `CURRENT` | `CURRENT` | Different Value | No Transition | `CONTRADICTION` | `ARCHIVE` | New active memory created; conflicting memory archived (`state = "archived"`, `is_contradicted = True`). |
| `FUTURE` | `CURRENT` | Different Value | N/A | `NEW` / `RELATED` | `STORE` | Both memories preserved as active records (`state = "active"`). |
| Negated ("no longer") | `CURRENT` | Same Value | N/A | `SUPERSESSION` | `UPDATE` | Existing fact marked historical without inventing fake dummy values (`"unknown"`). |

---

## Core Evolution Principles

### 1. Supersession vs. Contradiction
- **Supersession (`SUPERSESSION`)**: Fact transition over time. Old memory remains `state = "active"`, `is_contradicted = False`. Lineage is linked via existing `MemoryRelationship` table (`relationship_type = "superseded_by"`).
- **Contradiction (`CONTRADICTION`)**: Incompatible claims asserted for the same temporal scope without transition evidence. Old memory becomes `state = "archived"`, `is_contradicted = True`, `contradicted_by_id = new_memory_id`.

### 2. Historical Fact Preservation
- Historical facts remain queryable for past-oriented context queries (e.g. `"Where did I live before?"`).
- No database columns or tables were added; supersession uses the existing `MemoryRelationship` table.

### 3. "No-Longer" Negation Handling
- Statements like `"I do not live in Mumbai anymore."` transition the existing fact state to `HISTORICAL` without fabricating replacement values or dummy entries.

---

## v0.9 Additions

### Attribute Cardinality (`app/knowledge/attribute_schema.py`)
- Contradiction and supersession apply only to **single-valued** attributes:
  `residence`, `employer`, `name`, `age`, `favorite_*`, and
  LOCATION / EMPLOYMENT / PROFILE facts.
- Multi-valued attributes (preferences, devices, tools, learning topics,
  verb-derived relations) keep different values side by side:
  `"I like coffee."` + `"I like tea."` → two active memories.
- Unknown attributes default to multi-valued. A false contradiction archives a
  true memory; a missed one does not.

### Future Plans Are Protected
- A stored `FUTURE` fact is never contradicted or chosen as a supersession
  target by a different current value.
- Intention verbs create FUTURE facts: `"I am planning to move to Bangalore."`
  → `(user, residence, Bangalore, FUTURE)`.

### Re-assertion
- Re-stating a previously contradicted fact reactivates that memory (it is the
  newest explicit evidence). The competing claim is then contradicted.
  `Mumbai → Pune → Mumbai` ends with Mumbai active and Pune archived.
- A memory is never contradicted by itself. Archived merged duplicates are
  never resurrected.

### Lifecycle
- Decay demotes to `weak` and never archives.
- Access counting never moves a memory out of `archived`.
