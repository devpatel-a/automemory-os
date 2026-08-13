# Memory Importance Scoring

The Memory Engine assigns an importance score when a memory is created.

## Current Rule-Based Scores

The current implementation uses category-based importance:

| Category | Importance |
|---|---:|
| Profile | 0.95 |
| Preference | 0.80 |
| Habit | 0.70 |
| Event | 0.50 |
| Default | 0.40 |

These values are currently defined by the Memory Engine's
`calculate_importance()` function.

---

# Importance During Retrieval

Importance is no longer the only retrieval signal.

The current retrieval system combines importance with additional signals,
including:

- semantic relevance
- keyword relevance
- graph relevance
- recency
- access strength
- category relevance
- contradiction state

The current hybrid retrieval ranking is documented in:

`CURRENT_RETRIEVAL.md`

and:

`CURRENT_ARCHITECTURE.md`

Importance therefore acts as one ranking feature rather than being the
sole determinant of relevance.

---

# Memory Access Tracking

When memories are retrieved through the Memory Engine's retrieval
operations:

- `access_count` is incremented.
- `last_accessed` is updated.

These values provide additional information about memory usage.

Access strength is currently used as a weak ranking signal rather than
being allowed to dominate semantic relevance.

---

# Memory Search

The Memory Engine supports filtering by:

- Category
- Minimum importance
- Keyword

Keyword filtering uses SQL `ILIKE` for case-insensitive substring
matching in the direct memory-search functionality.

This direct keyword filtering is distinct from the current hybrid
retrieval system.

---

# Semantic Retrieval

Semantic vector retrieval is already implemented.

The current semantic retrieval system uses:

```text
SentenceTransformer
        ↓
384-dimensional embedding
        ↓
pgvector
        ↓
Cosine-distance search