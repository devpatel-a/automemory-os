# Current Testing Reference

## Overview

The repository contains a complete automated test suite covering memory persistence, vector search, knowledge graph indexing, memory evolution, hybrid candidate retrieval, context optimization, and v0.7 Memory Intelligence.

---

## Verified Test Execution Status

- **Full Test Suite Status**: **102 passed, 0 failed, 0 skipped**
- **Execution Time**: **23.96 seconds**
- **Verified Environment**: Verified in the development virtual environment.

### Test Execution Command

```bash
python -m pytest -q
```

---

## v0.7 Memory Intelligence Test Coverage (`test_memory_intelligence.py`)

The Memory Intelligence test suite verifies:

- **Acceptance Tests A–M**:
  - Test A: Preference extraction (`"I prefer espresso."`)
  - Test B: Location extraction (`"I live in Pune."`)
  - Test C: Employment extraction (`"I work at Google."`)
  - Test D: Learning topic extraction (`"I am learning FastAPI."`)
  - Test E: Multi-token value preservation (`"I live in New York."` $\rightarrow$ `New York`)
  - Test F: Paraphrase normalization across varied syntactic expressions (`"I live in Pune."`, `"I am living in Pune."`, `"My current city is Pune."`)
  - Test G: UPDATE classification for residence transitions (`Mumbai` $\rightarrow$ `Pune`)
  - Test H: REINFORCEMENT for duplicate preference claims
  - Test I: Unrelated facts (`location` vs `preference`) never UPDATE or MERGE
  - Test J: Contradiction operates strictly on comparable fact domains
  - Test K: Entity separation (`"My company is Google."` $\rightarrow$ entity=`user`, attribute=`employer`, value=`Google`)
  - Test L: Unknown/ambiguous input (`"I really like this."`) avoids hallucinating attributes
  - Test M: Generic extraction across coffee, city, company, programming, device, sport without domain-specific branches
- **Non-User Entity Extraction Tests**:
  - `"My friend Rahul works at Google."` $\rightarrow$ `entity = Rahul`, `attribute = employer`, `value = Google`
  - `"My brother lives in Pune."` $\rightarrow$ `entity = brother`, `attribute = residence`, `value = Pune`
- **Required Object-Context Tests**:
  - `"I use a MacBook Air."` $\rightarrow$ `attribute = device`, `fact_type = DEVICE`
  - `"I use a computer for work."` $\rightarrow$ `attribute = device`, `fact_type = DEVICE`
  - `"I use a workstation."` $\rightarrow$ `attribute = device`, `fact_type = DEVICE`
  - `"I use Python for work."` $\rightarrow$ `attribute = tool` / `usage` (NOT `device`)
  - `"I use Python."` $\rightarrow$ `attribute = tool` / `usage` (NOT `device`)
  - `"I use a programming language."` $\rightarrow$ `attribute = tool` / `usage` (NOT `device`)
- **Temporal Sentence Tests**:
  - `"I lived in Mumbai before moving to Pune."` $\rightarrow$ past temporal indicator detected, primary location Pune preserved. Verifies documented single-fact contract: compound sentences containing multiple temporal facts produce a single primary fact with coarse temporal information.
- **Negative Structural Tests**: Verifies non-user entities (`Rahul`, `brother`) are not converted to `user`, and verbs without device context (`use Python for work`) are not assigned `device`.
- **Confidence Monotonicity Tests**: Clear complete facts score higher confidence than ambiguous demonstrative text.
- **Memory Pipeline End-to-End Integration**: Raw input $\rightarrow$ `MemoryPipeline` $\rightarrow$ `Understanding` $\rightarrow$ `Knowledge` $\rightarrow$ `Decision` $\rightarrow$ `Memory Evolution`.

---

## Test Suite Module Distribution

| Test Module | Coverage Area |
| :--- | :--- |
| **`test_memory_intelligence.py`** | Generic linguistic fact extraction, attribute normalization, non-user entity extraction, conservative verb object semantics, paraphrase normalization, fact-driven UPDATE/MERGE/CONTRADICTION classification, confidence monotonicity, end-to-end `MemoryPipeline` integration. |
| **`test_context_optimization.py`** | Evidence relevance, current vs historical queries, contradiction lineage, merge safety, Jaccard diversity, multi-memory token budget (>1200 chars), negative cases A–J, empty candidate handling. |
| **`test_intelligent_retrieval.py`** | Candidate fusion across Semantic, Keyword, and Graph sources; single query embedding generation; active replacement ranking; robust graph term discovery; ContextEngine compatibility. |
| **`test_correctness_pass.py`** | Process-level shared graph state across `GraphService` instances; residence and workplace UPDATE transitions; unsafe update prevention; MERGE relationship safety without duplicate relationship records; MERGE state preservation; hybrid retrieval source integration. |
| **`test_evolution.py`** | Memory evolution state machine transitions (`create_memory`, `reinforce_existing_memory`, `update_existing_fact_memory`, `merge_existing_memories`, `contradict_existing_memory`). |
| **`test_contradiction.py`** | Contradiction detection rules, lineage linking (`contradicted_by_id`), and archival safety. |
| **`test_graph_repository.py` & `test_graph.py`** | In-memory graph node/edge storage, graph search indexing, and thread-safe process sharing. |
| **`test_context.py`** | ContextEngine multi-stage context building and token budget optimization. |