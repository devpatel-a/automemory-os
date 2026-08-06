# Semantic Storage

Every memory now stores both:

- Original text
- Embedding vector

Workflow:

User

↓

Embedding Model

↓

Vector

↓

PostgreSQL

This prepares AutoMemory OS for semantic retrieval using pgvector.