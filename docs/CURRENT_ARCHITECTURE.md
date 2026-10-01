# Current Architecture Reference

## Overview

AutoMemory OS is a 7-stage modular architecture for continuous user memory ingestion, evolution, candidate retrieval, context optimization, temporal fact reasoning, and knowledge graph integration.

---

## 7 Major Runtime Stages

```
Natural Language User Input
      ↓
1. Understanding Engine (app/understanding/):
   • spaCy NLP entity extraction & intent detection
   • Self/user pronoun resolution (I / me / my / myself → user entity)
   • Non-user grammatical subject resolution (Rahul, brother → distinct entities)
      ↓
2. Hybrid Candidate Retrieval (app/retrieval_service.py):
   • Semantic vector search (pgvector, cosine distance)
   • Lexical full-text search (PostgreSQL tsvector, whole words)
   • Knowledge Graph expansion (persistent graph, exact/alias entity resolution)
   • Multi-signal feature ranking (SEMANTIC 0.40, KEYWORD 0.20, GRAPH 0.15, IMPORTANCE 0.10, RECENCY 0.06, ACCESS 0.04, CATEGORY 0.05)
      ↓
3. Knowledge Reasoning Engine (app/knowledge/):
   • Generic linguistic fact extraction (extract_fact)
   • Entity Extraction → Attribute Extraction → Value Extraction → Fact Normalization → Temporal State → Relationship Context → Confidence
   • Generic spaCy dependency parsing, POS tags, noun chunks, grammatical subject, object structure
   • Zero memory-content value checks (no coffee, espresso, Pune, Google, Python, MacBook, iPhone, etc.)
   • Object Semantics: Deterministic & conservative classification (MacBook Air/computer/workstation → device vs Python/programming language → tool)
   • Structured fact domain comparison ((entity, attribute, value))
   • Knowledge Classification (NEW, REINFORCEMENT, UPDATE, MERGE, CONTRADICTION, SUPERSESSION, RELATED)
      ↓
4. Decision Engine (app/decision/):
   • Maps KnowledgeDecision → MemoryAction (STORE, REINFORCE, UPDATE, MERGE, ARCHIVE)
      ↓
5. Memory Evolution Engine (app/service.py):
   • Fact value transitions (SUPERSESSION) preserving historical memories in DB (state = "active")
   • Canonical memory consolidation with relationship transfer
   • Contradiction lineage linking only for genuine contradictions (`is_contradicted = True`, `contradicted_by_id = new_id`)
   • Supersession lineage uses `MemoryRelationship` (`relationship_type = "superseded_by"`) without contradiction flags
      ↓
6. Knowledge Graph Indexing (app/graph/):
   • Nodes (entities & concepts) and Edges (semantic relationships & explicit user relationships like friend_of, brother_of)
   • Persistent PostgreSQL graph (entities, aliases, memory links, typed relationships), written in the evolution transaction; process-local view kept for compatibility
      ↓
7. Context Engine (app/context/):
   • Evidence evaluation, conflict resolution, temporal query intent (CURRENT, HISTORICAL, FUTURE), Jaccard near-duplicate diversity, token budgeting (1200 chars), prompt package assembly (ContextPackage)
```

---

## Fact Representation (`KnowledgeFact`)

Memory Intelligence operates on five core semantic dimensions:

$$\text{ENTITY} + \text{ATTRIBUTE} + \text{VALUE} + \text{TEMPORAL STATE} + \text{RELATIONSHIP CONTEXT}$$

The structured fact model ([app/knowledge/fact_models.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/fact_models.py)) represents extracted natural language facts:

- **`entity`**: Resolved subject (`user` or non-user entity such as `Rahul`, `brother`).
- **`attribute`**: Normalized canonical property domain (`residence`, `employer`, `preference`, `learning_topic`, `device`, `tool`, `activity`, `profile`, `other`).
- **`value`**: Extracted value (multi-token phrase preserved, e.g. `New York`, `FastAPI`, `MacBook Air`).
- **`fact_type`**: Semantic classification (`LOCATION`, `EMPLOYMENT`, `PREFERENCE`, `LEARNING`, `DEVICE`, `HABIT`, `PROFILE`, `OTHER`).
- **`temporal_info`**: Coarse temporal signal (`current`, `past`, `future`).
- **`temporal_state`**: Explicit temporal state (`CURRENT`, `HISTORICAL`, `FUTURE`, `UNKNOWN`).
- **`relationship_to_user`**: Explicit entity-to-user relationship modifier (`friend`, `brother`, `colleague`, `boss`, etc., or `None` if unstated).
- **`is_negated`**: Negation modifier flag (`"no longer"`, `"not anymore"`).
- **`confidence`**: Deterministic score (`0.35` for ambiguous demonstratives, `0.60` base, up to `0.95` for complete facts).
- **`evidence_count`**: Frequency counter for memory reinforcement.
- **`contradiction_count`**: Historical contradiction tracking score.
- **`superseded_by_id`**: Runtime Memory ID reference linking superseded fact lineage.

---

## Temporal Fact States

- **`CURRENT`**: Facts representing the current state of truth (e.g. `"I live in Pune."`).
- **`HISTORICAL`**: Facts representing past truth that was later superseded or explicitly stated in the past tense (e.g. `"I used to live in Mumbai."` or `"I moved to Pune."`).
- **`FUTURE`**: Facts representing plans or predictions (e.g. `"I will move to Bangalore."`).
- **`UNKNOWN`**: Facts where temporal orientation is unspecified or ambiguous.

---

## Memory Lifecycle State vs. Fact Temporal State

AutoMemory OS strictly separates memory persistence lifecycle state from fact temporal state:

1. **Memory Lifecycle State (`Memory.state`)**:
   - `active`: Retrievable memory in active storage.
   - `weak`: Memory decaying towards archival due to low access frequency.
   - `archived`: Archived memory removed from default retrieval.

2. **Fact Temporal State (`Fact.temporal_state`)**:
   - `CURRENT`, `HISTORICAL`, `FUTURE`, `UNKNOWN`.

A historical fact (`temporal_state = "HISTORICAL"`) remains in an `active` `Memory` (`state = "active"`) so it can be retrieved for historical questions (e.g., `"Where did I live before?"`).

---

## Supersession vs. Contradiction

- **`SUPERSESSION != CONTRADICTION`**:
  - **`SUPERSESSION`**: Occurs when a fact transitions over time (e.g. `"I lived in Mumbai."` followed by `"I moved to Pune."`). The old fact (`Mumbai`) becomes `HISTORICAL` while remaining stored as `state = "active"` with `is_contradicted = False`. Lineage is linked via `MemoryRelationship` (`relationship_type = "superseded_by"`).
  - **`CONTRADICTION`**: Occurs when conflicting current assertions are made without transition evidence (e.g. `"I live in Mumbai."` followed by `"I live in Pune."`). The old conflicting memory is archived (`state = "archived"`, `is_contradicted = True`, `contradicted_by_id = new_memory_id`).

---

## v0.9 Notes

- **Attribute cardinality:** only single-valued attributes (residence,
  employer, name, …) can be contradicted or superseded. Multi-valued ones
  (preferences, devices, tools) coexist. See `CURRENT_MEMORY_EVOLUTION.md`.
- **Temporal cues** live in `app/knowledge/temporal_cues.py` and match whole
  words only.
- **Configuration:** `app/config.py` (`DATABASE_URL`, `EMBEDDING_MODEL`,
  `CONTEXT_RETRIEVAL_LIMIT`, `CONTEXT_TOKEN_BUDGET`).
- **Audit and gap analysis:** `ARCHITECTURE_ASSESSMENT.md`. **Measurement:** `EVALUATION.md`.

---

## v0.10 Notes (hardening)

- **Evolution** executes exactly one handler per knowledge decision, on the exact
  target chosen by the classifier, atomically (one transaction: memory, lineage,
  graph and evidence), with row locks and retry on concurrent conflicts.
- **Persistence:** Alembic migrations (`services/memory-service/alembic`), database
  constraints, persistent graph, provenance (`memory_evidence`).
- **Lineage:** `superseded_by`, `merged_into`, `fulfilled_by` in `memory_relationships`;
  contradiction on the memory row (`contradicted_by_id`, FK).
- **Startup validation:** spaCy model, embedding dimension vs. `vector(384)`, database.
- See `ARCHITECTURE_ASSESSMENT.md` §7 for the v0.10 record.

---

## v0.11 (in progress): `knowledge_facts` shadow index

A derived, rebuildable index of each memory's structured fact (`knowledge_facts`,
migration 0006). `memories.content` remains the source of truth. Lifecycle and
lineage are not copied into the index. It is written in the same transaction
as content changes, but **not yet used** by evolution, classification or
retrieval. Design: `docs/design/KNOWLEDGE_FACTS_INDEX.md`.
