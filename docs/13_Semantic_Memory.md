# Semantic Memory

## Purpose

Semantic Memory enables AutoMemory OS to retrieve memories based on semantic meaning rather than exact keyword matches.

---

## Historical Context

In early versions of AutoMemory OS, memory retrieval relied exclusively on exact SQL keyword matching (`ILIKE`). While effective for exact term lookup, keyword matching failed for semantically equivalent phrasing (e.g., "beverage" vs "drink").

---

## Current Implementation

Semantic memory is fully implemented using vector embeddings and vector similarity search.

### Key Components

- **Embedding Model**: `SentenceTransformer("all-MiniLM-L6-v2")` generates 384-dimensional dense floating-point vector representations for memory contents.
- **Vector Persistence**: Embeddings are stored in PostgreSQL using the `pgvector` extension (`Vector(384)` column on the `memories` table).
- **Similarity Search**: Cosine distance (`Memory.embedding.cosine_distance(embedding)`) is computed directly in PostgreSQL.
- **Service Integration**: [app/semantic/semantic_service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/semantic/semantic_service.py) provides `generate_embedding(text)` and `semantic_search(db, query, limit=20, query_embedding=None)`.
- **Retrieval Pipeline Integration**: [app/retrieval_service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/retrieval_service.py) reuses precomputed query embeddings to perform semantic vector search as the primary candidate discovery layer.

---

## Dependencies

- `sentence-transformers`
- `pgvector` (PostgreSQL extension)
- `SQLAlchemy`