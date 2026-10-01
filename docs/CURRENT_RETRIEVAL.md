# Current Retrieval Reference

## Architecture & System Roles

Retrieval operates in tandem with Memory Intelligence and Context Engine:

1. **Memory Intelligence**: Determines the semantic and temporal meaning of extracted facts (`CURRENT`, `HISTORICAL`, `FUTURE`).
2. **Retrieval Service**: Fetches candidate memories using hybrid semantic vector search, keyword text matching, and graph traversal.
3. **Context Engine**: Evaluates query temporal intent and selects/ranks candidate memories for final context assembly.

---

## Hybrid Candidate Retrieval Mechanics

Candidate retrieval fetches top memory candidates using multi-signal feature scoring:

- **Semantic Vector Search (`pgvector`)**: Cosine distance on embedding representations ($40\%$ weight).
- **Lexical Search (PostgreSQL full-text search)**: Whole-word matching via `to_tsvector('english')` and the GIN index `ix_memories_content_fts`; scored on whole-word tokens ($20\%$ weight). `car` never matches `career`.
- **Graph Expansion (persistent graph)**: memories linked to entities resolved from the query by exact normalized name or explicit alias, longest span first ($15\%$ weight).
- **Importance, Recency, Access, Category**: Auxiliary ranking signals ($25\%$ combined weight).

---

## Temporal Query Intent & Context Ranking

The Context Engine resolves candidate memories against user query intent:

- **Current Query Intent** (e.g., `"What city do I live in?"`):
  - Prioritizes memories with `temporal_state = "CURRENT"` (e.g. `"I moved to Pune."`).
- **Historical Query Intent** (e.g., `"Where did I live before?"`):
  - Prioritizes memories with `temporal_state = "HISTORICAL"` or superseded lineage (e.g. `"I lived in Mumbai."`).
- **Future Query Intent** (e.g., `"Where will I live?"`):
  - Prioritizes memories with `temporal_state = "FUTURE"` (e.g. `"I will move to Bangalore."`).

---

## v0.10: Lifecycle Scopes, Structured Candidates, Lexical Matching

### Lifecycle scopes (enforced at the source)
| Call | Returns |
| :--- | :--- |
| `semantic_search(...)` / `retrieve_memories(...)` (default) | live memories: `active` + `weak` (superseded memories stay `active`, so history remains reachable) |
| `include_archived=True` | also archived merged duplicates and contradicted claims (historical queries, audit) |

The evolution pipeline never uses archived memories as candidates.

### Structured candidates
`retrieve_candidates()` returns `RetrievalCandidate` objects (`app/retrieval_models.py`)
with separate signals: `semantic_score`, `lexical_score`, `graph_score`, `importance`,
`recency`, `access_frequency`, `category_score`, `retrieval_score`, plus the context-stage
`entity_score`, `attribute_score`, `temporal_score` (and a reserved, currently unmeasured
`relationship_score`), `confidence`, `lifecycle_state`, `temporal_state`, `final_score`
and `reasons` (`semantic_match`, `lexical_match`, `graph_entity_match`, ...).
`retrieve_memories()` keeps its `[(Memory, score)]` contract.

### Candidate pools
Semantic: 20, lexical: 30 (bounded per signal), graph: all memories linked to the
resolved query entities.

### Vector index
No approximate (HNSW/IVFFlat) index yet: pgvector's HNSW skips NULL embeddings and
post-filters lifecycle predicates, which silently drops candidates. Exact scans are
used until measured volume requires ANN (see `KNOWN_LIMITATIONS.md`).
