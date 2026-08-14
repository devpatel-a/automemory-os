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
