# Known Limitations & System Boundaries

## Design Philosophy

AutoMemory OS intentionally relies on deterministic NLP algorithms, explicit dependency parsing, and structured database operations rather than non-deterministic Large Language Models (LLMs) or external cloud APIs. These operational boundaries define the scope of current capabilities.

---

## Technical & Architecture Boundaries

### 1. Deterministic Temporal Reasoning
- Temporal state classification (`CURRENT`, `HISTORICAL`, `FUTURE`) relies on spaCy verb tags, temporal indicators, and transition phrasing.
- Complex multi-event temporal narratives in a single sentence (e.g. `"Before living in Mumbai, I lived in Pune after moving from Delhi."`) are extracted as a primary fact rather than decomposed into multiple linked historical records.

### 2. Conservative Entity Resolution
- Entity resolution uses explicit entity/dependency structure and conservative contextual matching to avoid false merges.
- Similar names are not automatically treated as the same entity (`Rahul Patel` vs `Rahul Sharma`).
- Coreference resolution across separate distant conversations (e.g. resolving `"he"` to `Rahul` without explicit context) remains intentionally constrained.

### 3. Future Fact State Lifecycle
- Future plans (e.g. `"I will move to Bangalore next month."`) are stored with `temporal_state = "FUTURE"`.
- Future facts do not automatically transition to `CURRENT` based on system clock elapsed time without user input confirming the transition.

### 4. Graph Relationship Extraction Scope
- Knowledge graph edge extraction uses deterministic rule maps and POS structures.
- Implicit or nuanced interpersonal relationships unstated in text are not inferred or hallucinated.

### 5. Non-Probabilistic Storage
- AutoMemory OS uses discrete confidence scores and state flags rather than probabilistic graphical models.

---

## Status of v0.9 Audit Findings (v0.10)

| Finding | Status |
| :--- | :--- |
| Keyword entity list (domain hard-coding) | **Resolved**: generic noun-chunk + NER entities |
| Graph not persisted | **Resolved**: PostgreSQL graph, written in the evolution transaction |
| Substring entity matching | **Resolved**: exact normalized name / explicit alias, longest span |
| No provenance | **Resolved**: `memory_evidence` (append-only; legacy rows marked `legacy`) |
| MERGE loses original statements | **Resolved**: evidence keeps every statement; `merged_into` lineage |
| Fulfilled plans merged away | **Resolved**: never merged; `fulfilled_by` lineage |
| Tests share the configured database | **Resolved**: tests refuse non-test databases |
| Facts re-extracted on every use | **Mitigated**: bounded parse cache (~19x faster context builds); no stored facts table yet |
| Top-5 evolution candidate pool | **Open**: see below |

## Remaining Limitations (v0.10)

- **Evolution candidate pool:** classification still sees the top-5 semantic
  neighbours (plus a 50-candidate wide search only to resolve a contradiction
  target). A conflicting same-attribute fact outside that pool is missed.
  A stored `knowledge_facts` table with an `(entity, attribute)` index is the fix.
- **Entity identity by name:** two different people who share exactly the same
  name are one entity until an alias/disambiguation mechanism exists
  (resolution never merges *different* names).
- **No context-supported coreference:** "he", "my friend" across messages are not
  resolved to entities.
- **No ANN vector index:** exact cosine scans; add HNSW/IVFFlat (with iterative
  scans for filtered queries) when measured data volume requires it.
- **`relationship_score`** is reserved in `RetrievalCandidate` but not measured.
- **Attribute cardinality** is a small static schema; unknown attributes are
  treated as multi-valued (never contradicted).
- **Legacy endpoints:** `GET /context` still uses the legacy
  `context_service` (ILIKE over the whole query) rather than the ContextEngine;
  kept for API compatibility.
- **Lifecycle quirk:** reinforcement with `access_count < 3` sets `weak` (still retrievable).
