# AutoMemory OS Roadmap

## Overview

This roadmap clearly demarcates implemented functionality, partial foundations, planned future milestones, and technical debt.

---

## 1. IMPLEMENTED

- [x] **Core Memory Storage & Vector Search**: PostgreSQL + `pgvector` embedding storage (`Vector(384)`) using `SentenceTransformer("all-MiniLM-L6-v2")`.
- [x] **Current Ingestion & Evolution Pipeline**: `MemoryPipeline` orchestrating Understanding → Candidate Retrieval → Knowledge Processing → Decision → Memory Evolution → Knowledge Graph.
- [x] **Memory Evolution Actions**:
  - `STORE`: New memory persistence.
  - `REINFORCE`: Exact duplicate strengthening.
  - `UPDATE`: Fact value transitions on normalized entity + attribute.
  - `MERGE`: Canonical memory consolidation with relationship transfer and redundant memory archival.
  - `CONTRADICTION`: Exact target contradiction identification, setting `is_contradicted = True` and `contradicted_by_id`.
- [x] **Intelligent Hybrid Candidate Fusion**: Candidate deduplication map combining Semantic Vector Search, Keyword Search, and Knowledge Graph Expansion with single query embedding generation.
- [x] **Multi-Signal Feature Ranking**: Deterministic `[0, 1]` score normalization using explicit weights (`SEMANTIC_WEIGHT = 0.40`, `KEYWORD_WEIGHT = 0.20`, `GRAPH_WEIGHT = 0.15`, `IMPORTANCE_WEIGHT = 0.10`, `RECENCY_WEIGHT = 0.06`, `ACCESS_WEIGHT = 0.04`, `CATEGORY_WEIGHT = 0.05`, `CONTRADICTION_PENALTY = 0.80`).
- [x] **v0.6 Context Optimization / Context Quality**: Evidence evaluation, conflict resolution, historical query candidate retrieval, near-duplicate Jaccard diversity, token budgeting (1200 chars), and structured `ContextPackage` assembly.
- [x] **v0.7 Memory Intelligence**:
  - v0.7 Memory Intelligence was implemented and verified with the full test suite. The milestone introduces structured fact extraction, entity/attribute/value representation, generic linguistic normalization, structured knowledge classification, and improved Memory Evolution safety.
  - Generic linguistic fact representation (`entity`, `attribute`, `value`, `fact_type`, `temporal_info`, `confidence`).
  - spaCy dependency parsing & centralized canonical attribute normalization layer in `app/knowledge/fact_extractor.py`.
  - Non-user entity resolution (Rahul, brother) vs self/user entity mapping.
  - Purely linguistic context-aware verb object semantics (distinguishing `I use a MacBook Air` $\rightarrow$ `device` vs `I use Python for work` $\rightarrow$ `tool` without product-name keywords).
  - Fact domain classification (`(entity, attribute, value)` comparison) for UPDATE, MERGE, REINFORCEMENT, and CONTRADICTION actions.

---

## 2. PARTIAL / IN-PROGRESS FOUNDATIONS

- [ ] **Knowledge Graph Persistence**: Currently process-shared in-memory state (`GraphRepository`). Needs persistent storage backend (Neo4j or PostgreSQL graph tables) across service restarts.
- [ ] **Relationship Extraction**: Basic `related_to` relationship tracking. Deep semantic relationship taxonomy requires expansion.

---

## 3. PLANNED MILESTONES

- [ ] **LLM Context Integration**: Prompt template formatting and LLM provider integration.
- [ ] **Distributed Graph Storage**: Persistent multi-hop graph database.
- [ ] **Multi-Agent Memory Partitioning**: Namespace & tenant isolation for multi-agent OS environments.

---

## 4. TECHNICAL DEBT & KNOWN LIMITATIONS

- [ ] **Single-Fact Extraction Limitation**: Multi-clause compound sentences ("I lived in Mumbai before moving to Pune.") currently extract the primary active fact while capturing temporal indicators.
- [ ] **Targeted Historical Retrieval**: Historical mode can expose a broader archived candidate pool than strictly necessary; future retrieval improvements should make historical candidate discovery more targeted.
- [ ] **Process-Local In-Memory Graph**: In-memory graph state is not shared across multi-process worker deployments or persistent across server restarts.
- [ ] **Dual Orchestration Paths**: `MemoryOrchestrator` exists alongside `MemoryPipeline`. `MemoryOrchestrator` should eventually be deprecated or refactored into a thin wrapper around `MemoryPipeline`.