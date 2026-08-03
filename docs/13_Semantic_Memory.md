# Semantic Memory

Semantic Memory enables AutoMemory OS to retrieve memories based on meaning rather than exact keywords.

Instead of comparing text directly, the system converts both user queries and memories into embeddings.

Similar meanings produce similar vectors, allowing the Context Engine to retrieve semantically related memories.

Current implementation:
- Keyword search (ILIKE)

Future implementation:
- Sentence embeddings
- Vector similarity search
- Semantic retrieval