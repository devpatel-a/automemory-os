# Current Architecture Reference

## Overview

AutoMemory OS is a 7-stage modular architecture for continuous user memory ingestion, evolution, candidate retrieval, context optimization, and knowledge graph reasoning.

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
   • Keyword text search (SQL ILIKE)
   • Knowledge Graph expansion (GraphSearch)
   • Multi-signal feature ranking (SEMANTIC 0.40, KEYWORD 0.20, GRAPH 0.15, IMPORTANCE 0.10, RECENCY 0.06, ACCESS 0.04, CATEGORY 0.05)
      ↓
3. Knowledge Reasoning Engine (app/knowledge/):
   • Generic linguistic fact extraction (extract_fact)
   • Entity Extraction → Attribute Extraction → Value Extraction → Fact Normalization → Fact Type → Temporal Info → Confidence
   • Generic spaCy dependency parsing, POS tags, noun chunks, grammatical subject, object structure
   • Zero memory-content value checks (no coffee, espresso, Pune, Google, Python, MacBook, iPhone, etc.)
   • Object Semantics: Deterministic & conservative classification (MacBook Air/computer/workstation → device vs Python/programming language → tool)
   • Structured fact domain comparison ((entity, attribute, value))
   • Knowledge Classification (NEW, REINFORCEMENT, UPDATE, MERGE, CONTRADICTION, RELATED)
      ↓
4. Decision Engine (app/decision/):
   • Maps KnowledgeDecision → MemoryAction (STORE, REINFORCE, UPDATE, MERGE, ARCHIVE)
      ↓
5. Memory Evolution Engine (app/service.py):
   • In-place fact value updates (is_contradicted = False)
   • Canonical memory consolidation with relationship transfer
   • Contradiction target lineage linking (is_contradicted = True, contradicted_by_id = new_id)
      ↓
6. Knowledge Graph Indexing (app/graph/):
   • Nodes (entities & concepts) and Edges (semantic relationships)
   • Thread-safe process-shared graph repository
      ↓
7. Context Engine (app/context/):
   • Evidence evaluation, conflict resolution, historical retrieval, Jaccard near-duplicate diversity, token budgeting (1200 chars), prompt package assembly (ContextPackage)
```

---

## Structured Fact Representation (`KnowledgeFact`)

The structured fact model ([app/knowledge/fact_models.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/fact_models.py)) represents extracted natural language facts:

- **`entity`**: Resolved subject (`user` or non-user entity such as `Rahul`, `brother`).
- **`attribute`**: Normalized canonical property domain (`residence`, `employer`, `preference`, `learning_topic`, `device`, `tool`, `activity`, `profile`, `other`).
- **`value`**: Extracted value (multi-token phrase preserved, e.g. `New York`, `FastAPI`, `MacBook Air`).
- **`fact_type`**: Semantic classification (`LOCATION`, `EMPLOYMENT`, `PREFERENCE`, `LEARNING`, `DEVICE`, `HABIT`, `PROFILE`, `OTHER`).
- **`temporal_info`**: Coarse temporal signal (`current`, `past`, `future`).
- **`confidence`**: Deterministic score (`0.35` for ambiguous demonstratives, `0.60` base, up to `0.95` for complete facts).
- **`evidence_count`**: Frequency counter for memory reinforcement.
- **`contradiction_count`**: Historical contradiction tracking score.