# AutoMemory OS Project Roadmap

## Completed Milestones

### v0.3 — Database & Semantic Core [COMPLETE]
- PostgreSQL database integration with SQLAlchemy ORM.
- `pgvector` semantic embedding storage & cosine similarity search.
- Semantic duplicate detection and memory strengthening.

### v0.4 — Context Optimization Engine [COMPLETE]
- Context Engine implementation with token budgeting (1200 chars).
- Jaccard near-duplicate diversity filtering (0.85 threshold).
- Category-based prompt package formatting (`ContextPackage`).

### v0.5 — Knowledge Classification & Evolution [COMPLETE]
- Knowledge classification pipeline (`NEW`, `REINFORCEMENT`, `UPDATE`, `MERGE`, `CONTRADICTION`).
- In-place memory updates and canonical merge consolidation.
- Contradiction detection and memory archival.

### v0.6 — Process-Shared Knowledge Graph [COMPLETE]
- Thread-safe process-shared Knowledge Graph.
- Hybrid Candidate Retrieval combining vector search, keyword matching, and graph traversal.
- Multi-signal candidate ranking.

### v0.7 — Memory Intelligence & Generalization Pass [COMPLETE]
- Structured `KnowledgeFact` representation (`entity`, `attribute`, `value`, `fact_type`).
- Zero product-specific hardcoding rule enforced across all domains.
- Non-user entity extraction (`Rahul`, `brother`).
- Conservative object semantics (`device` vs `tool`).
- 102 verified unit and integration tests passing cleanly.

### v0.8 — Temporal + Entity Reasoning [COMPLETE]
- **Temporal Fact State Reasoning**: Structured temporal states (`CURRENT`, `HISTORICAL`, `FUTURE`, `UNKNOWN`).
- **Historical Fact Preservation**: Superseded memories remain stored with `state = "active"` and `is_contradicted = False` for historical retrieval.
- **Fact Supersession Lineage**: Linked via `MemoryRelationship` table (`relationship_type = "superseded_by"`).
- **Contradiction Separation**: Incompatible current claims without transition evidence trigger contradiction archival (`is_contradicted = True`, `state = "archived"`).
- **Future Fact Preservation**: Planned facts preserved alongside current facts without premature overwrite.
- **"No-Longer" Negation Semantics**: Negated transition statements update existing facts to `HISTORICAL` without fabricating dummy values.
- **Explicit Entity Relationships & Graph Safety**: Subject resolution prevents false user-relationship edge generation (`Rahul works at Google` $\rightarrow$ `rahul --works_at--> google`).
- **Conservative Entity Resolution**: Distinguishes distinct entity instances (`Rahul Patel` vs `Rahul Sharma`).
- **Temporal Query Handling**: Context Engine ranks candidate memories according to query temporal intent (`CURRENT`, `HISTORICAL`, `FUTURE`).
- **116/116 Tests Passing**: Verified full test suite execution in 20.17 seconds.

### v0.9 — Correctness, Query-Aware Context & Evaluation [COMPLETE]
- **Evaluation framework** (`app/evaluation/`): P@1, Recall@k, MRR, nDCG,
  lineage precision/recall, graph edge accuracy, duplicate suppression,
  extraction and temporal accuracy, plus a regression gate.
- **Correctness fixes** measured by the framework: word-boundary temporal cues,
  decay never archives, re-assertion safety, attribute cardinality,
  direct-object values, planned (FUTURE) facts, `used to` aspect.
- **Query-aware context:** `QueryIntent`, lineage-aware temporal conflict
  resolution, structured `ContextEvidence` in `ContextPackage`.
- **Typed configuration** (`app/config.py`).
- **149/149 tests passing.**

## Next Milestones (proposed, see ARCHITECTURE_ASSESSMENT.md §5)
1. Test database safety and Alembic migrations.
2. First-class provenance (`memory_evidence`, `merged_into` lineage).
3. Stored canonical facts with structural candidate lookup.
4. Persisted, conservatively resolved entity graph; remove the keyword entity list.
5. Temporal events and explicit uncertainty, driven by measured failures.
