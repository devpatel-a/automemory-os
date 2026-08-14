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
- **Keyword Text Search (SQL `ILIKE`)**: Lexical substring matching ($20\%$ weight).
- **Graph Expansion (`GraphSearch`)**: Entity node memory references ($15\%$ weight).
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
