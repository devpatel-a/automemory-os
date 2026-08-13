# AutoMemory OS Roadmap

## Overview

This roadmap clearly demarcates implemented functionality, partial foundations, planned future milestones, and technical debt.

---

## 1. IMPLEMENTED

- [x] **Core Memory Storage & Vector Search**: PostgreSQL + `pgvector` embedding storage (`Vector(384)`) using `SentenceTransformer("all-MiniLM-L6-v2")`.
- [x] **10-Tier Ingestion & Evolution Pipeline**: `MemoryPipeline` orchestrating Understanding → Candidate Retrieval → Knowledge Processor → Decision Engine → Evolution Engine → Knowledge Graph.
- [x] **Memory Evolution Actions**:
  - `STORE`: New memory persistence.
  - `REINFORCE`: Exact duplicate strengthening.
  - `UPDATE`: Fact value transitions on normalized entity + attribute.
  - `MERGE`: Canonical memory consolidation with relationship transfer and redundant memory archival.
  - `CONTRADICTION`: Exact target contradiction identification, setting `is_contradicted = True` and `contradicted_by_id`.
- [x] **Intelligent Hybrid Candidate Fusion**: Candidate deduplication map combining Semantic Vector Search, Keyword Search, and Knowledge Graph Expansion with single query embedding generation.
- [x] **Multi-Signal Feature Ranking**: Deterministic `[0, 1]` score normalization using explicit weights (`SEMANTIC_WEIGHT = 0.40`, `KEYWORD_WEIGHT = 0.20`, `GRAPH_WEIGHT = 0.15`, `IMPORTANCE_WEIGHT = 0.10`, `RECENCY_WEIGHT = 0.06`, `ACCESS_WEIGHT = 0.04`, `CATEGORY_WEIGHT = 0.05`, `CONTRADICTION_PENALTY = 0.80`).

---

## 2. PARTIAL / IN-PROGRESS FOUNDATIONS

- 🟡 **v0.6 Context Optimization / Context Quality (In Progress)**:
  - Evidence Evaluation (`app/context/evidence_evaluator.py`) combining base retrieval score, exact entity match, structured fact attribute match, category match, and temporal match.
  - Conflict Resolver (`app/context/conflict_resolver.py`) resolving fact domain conflicts, enforcing contradiction lineage (`contradicted_by_id`), merge safety, and current vs historical query handling.
  - Near-duplicate diversity optimization (`diversity.py`), token budgeting (1200 chars), and context prompt package assembly (`ContextPackage`).
- [ ] **Knowledge Graph Persistence**: Currently process-shared in-memory state (`GraphRepository`). Needs persistent storage backend (Neo4j or PostgreSQL graph tables) across service restarts.
- [ ] **Relationship Extraction**: Basic `related_to` relationship tracking. Deep semantic relationship taxonomy requires expansion.

---

## 3. PLANNED

- [ ] **Memory Intelligence Milestone**: Richer natural language fact understanding and universal fact schema parsing.
- [ ] **LLM Context Integration**: Prompt template formatting and LLM provider integration.
- [ ] **Distributed Graph Storage**: Persistent multi-hop graph database.
- [ ] **Multi-Agent Memory Partitioning**: Namespace & tenant isolation for multi-agent OS environments.

---

## 4. TECHNICAL DEBT & KNOWN LIMITATIONS

- [ ] **Targeted Historical Retrieval**: Historical mode can expose a broader archived candidate pool than strictly necessary; future retrieval improvements should make historical candidate discovery more targeted.
- [ ] **Process-Local In-Memory Graph**: In-memory graph state is not shared across multi-process worker deployments or persistent across server restarts.
- [ ] **Dual Orchestration Paths**: `MemoryOrchestrator` exists alongside `MemoryPipeline`. `MemoryOrchestrator` should eventually be deprecated or refactored into a thin wrapper around `MemoryPipeline`.