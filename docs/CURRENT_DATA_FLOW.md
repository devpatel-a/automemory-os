# Current Data Flow Reference

## End-to-End System Data Flow

```
                  User Natural Language Input
                              │
                              ▼
                   1. Understanding Engine
               (Parsing & Intent Detection)
                              │
                              ▼
               2. Structured Fact Extraction
        (Entity, Attribute, Value Extraction)
                              │
                              ▼
             3. Temporal + Entity Reasoning
     (Temporal State, Negation & Subject Resolution)
                              │
                              ▼
                 4. Candidate Retrieval
       (Semantic Vector + Keyword + Graph Search)
                              │
                              ▼
              5. Knowledge Classification
        (Decision Matrix: NEW, UPDATE, MERGE, etc.)
                              │
                              ▼
                    6. Decision Engine
              (Maps Decision → MemoryAction)
                              │
                              ▼
                 7. Memory Evolution Engine
       (Store / Reinforce / Supersede / Merge / Archive)
                              │
                              ▼
                8. Knowledge Graph Indexing
          (Process-shared Entity/Concept Graph)
                              │
                              ▼
                   9. Hybrid Retrieval
        (Query Intent & Multi-Signal Scoring)
                              │
                              ▼
                   10. Context Engine
        (Temporal Intent Ranking & Assembly)
                              │
                              ▼
                    Final Context Package
```

---

## Detailed Data Flow Stages

### 1. Understanding & Structured Fact Extraction
- Natural language input is parsed using spaCy NLP.
- Subject pronouns (`I`, `me`, `my`, `myself`) resolve to `user`. Non-user subjects (`Rahul`, `brother`) resolve to specific entity nodes.
- Facts are structured into `KnowledgeFact`: `(entity, attribute, value, fact_type, temporal_info, temporal_state, relationship_to_user, is_negated, confidence)`.

### 2. Temporal + Entity Reasoning (v0.8 Integration Layer)
- Evaluates temporal indicators (`past`, `future`, transition phrasing like `"moved to"`, `"transferred to"`).
- Determines `temporal_state`: `CURRENT`, `HISTORICAL`, `FUTURE`, `UNKNOWN`.
- Detects negation (`is_negated = True`) for "no longer" statements.
- Resolves explicit entity relationships (`relationship_to_user = "friend"` for `"My friend Rahul"`).

### 3. Candidate Retrieval
- Fetches top candidates from PostgreSQL via semantic embeddings (`pgvector` cosine distance) and keyword matching (`ILIKE`).

### 4. Knowledge Classification & Decision
- Evaluates incoming fact against candidate memories using the v0.8 decision matrix.
- Maps `KnowledgeDecision` (`NEW`, `REINFORCEMENT`, `UPDATE`, `SUPERSESSION`, `MERGE`, `CONTRADICTION`, `RELATED`) to `MemoryAction` (`STORE`, `REINFORCE`, `UPDATE`, `MERGE`, `ARCHIVE`).

### 5. Memory Evolution & Knowledge Graph
- **SUPERSESSION**: Creates a new active memory record for the current fact, preserves the existing memory in PostgreSQL (`state = "active"`), and links supersession lineage in `MemoryRelationship` (`relationship_type = "superseded_by"`).
- **CONTRADICTION**: Archives conflicting current claims without transition evidence (`state = "archived"`, `is_contradicted = True`).
- Updates thread-safe process-shared Knowledge Graph.

### 6. Hybrid Retrieval & Context Assembly
- `ContextEngine` identifies query temporal intent (`CURRENT`, `HISTORICAL`, `FUTURE`).
- Ranks candidate memories prioritizing `CURRENT` facts for location/employment queries and `HISTORICAL` facts for historical queries (`"Where did I live before?"`).
- Packages selected memories into `ContextPackage` within a 1200 character budget.
