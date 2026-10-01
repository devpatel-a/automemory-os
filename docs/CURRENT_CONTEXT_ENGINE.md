# Current Context Engine Reference

## Overview

The Context Engine (`app/context/context_engine.py`) formats retrieved memories into structured prompt packages (`ContextPackage`) for downstream application consumption.

---

## 7-Step Optimization Pipeline

```
Retrieved Candidate Memories
             ↓
1. Entity Matching: Boosts candidates sharing query entities
             ↓
2. Category Matching: Boosts candidates matching query intent categories
             ↓
3. Temporal Intent Matching (v0.8): Evaluates query temporal orientation
             ↓
4. Multi-Signal Ranking: Computes composite candidate score
             ↓
5. Jaccard Near-Duplicate Filtering: Ensures candidate diversity (threshold 0.85)
             ↓
6. Token Budgeting: Hard limit of 1200 characters
             ↓
7. Prompt Context Assembly: Produces ContextPackage (profile, preferences, habits, events, other)
```

---

## Temporal Query Intent & Evidence Ranking (v0.8)

The Context Engine analyzes query temporal keywords to determine evidence preference:

- **`CURRENT` Query Intent**:
  - Example: `"What city do I live in?"` or `"Where do I work?"`
  - Prefers active current facts (`"I moved to Pune."`, `"I work at Apple."`).
- **`HISTORICAL` Query Intent**:
  - Example: `"Where did I live before?"` or `"What was my previous job?"`
  - Prefers historical facts and superseded memories (`"I lived in Mumbai."`, `"I worked at Google."`).
- **`FUTURE` Query Intent**:
  - Example: `"Where will I move?"` or `"What are my future plans?"`
  - Prefers planned future facts (`"I will move to Bangalore."`).

Historical memories remain stored as active database records (`state = "active"`), ensuring they are available for historical questions rather than being archived simply because a newer fact was recorded.

---

## Output Structure (`ContextPackage`)

Context packages present selected memories organized by functional category:

- `profile`: Core demographic facts and residence.
- `preferences`: User likes, dislikes, favorite items.
- `habits`: Recurring routines and daily practices.
- `events`: Historical occurrences and milestones.
- `other`: Additional facts and general entity relationships.

---

## v0.9: Query-Aware, Lineage-Aware Context

### Query Intent (`app/context/query_intent.py`)
`analyze_query()` returns `QueryIntent(entity, attribute, temporal_intent)`:

| Query | entity | attribute | temporal_intent |
| :--- | :--- | :--- | :--- |
| "What city do I live in?" | user | residence | CURRENT |
| "Where did I live before?" | user | residence | HISTORICAL |
| "Where am I planning to move?" | user | residence | FUTURE |

### Effective Temporal State
A memory with a `superseded_by` lineage link is **HISTORICAL**, whatever its
text says. Lineage for all candidates is loaded in one query.

### Conflict Resolution
Facts compete per domain key: `(entity, attribute)` for single-valued
attributes, `(entity, attribute, value)` for multi-valued ones. Winners are
chosen by an explicit temporal priority:

| Query intent | Priority |
| :--- | :--- |
| CURRENT | CURRENT > UNKNOWN > HISTORICAL > FUTURE |
| FUTURE | FUTURE > CURRENT > UNKNOWN > HISTORICAL |
| HISTORICAL | every version is kept |

Ties are broken by contradiction lineage, then recency (`created_at`, then id).
A plan can never answer a current question.

### Temporal Alignment
Candidates whose effective temporal state matches the query intent receive
`TEMPORAL_ALIGNMENT_BONUS` (0.25), so historical facts rank first for
historical queries.

### Structured Evidence
`ContextPackage` keeps its text buckets and adds:
- `intent`: the `QueryIntent`.
- `evidence`: one `ContextEvidence` per selected memory, in rank order, with
  `memory_id`, `entity`/`attribute`/`value`, `temporal_state`,
  `lifecycle_state`, `confidence`, `score` and machine-readable `reasons`.

### Configuration
`CONTEXT_RETRIEVAL_LIMIT` (default 10) and `CONTEXT_TOKEN_BUDGET` (default 1200
characters) come from `app/config.py`.

---

## v0.10

- `build_context(db, query, limit=None)`: `limit` caps the selection. The agent
  passes `top_k`, and its `memories_used` are exactly `package.evidence`.
- `ContextEvidence.signals` exposes each candidate's independently measured
  signals (semantic, lexical, graph, entity, attribute, temporal, final, ...).
- Historical lineage covers `superseded_by` and `fulfilled_by`. A fulfilled plan
  is effectively HISTORICAL but gets no historical-alignment bonus (it was a
  plan, not a past state).
- Matching of entities, categories and temporal words is whole-word.
