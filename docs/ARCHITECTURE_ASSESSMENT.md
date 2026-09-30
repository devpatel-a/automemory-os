# Architecture Assessment (v0.8 → v0.9)

This is a source-first audit of the v0.8 repository and the record of the v0.9
correctness pass. Where documentation and implementation disagreed, the
implementation plus tests were treated as the source of truth, and the
discrepancy is listed below.

---

## 1. How the audit was done

1. Read every module under `services/memory-service/app/` and all `docs/CURRENT_*.md`.
2. Reproduced the documented baseline: **116 / 116 tests pass**.
3. Ran the benchmark scenarios from the engineering brief end to end through
   `MemoryPipeline` and `ContextEngine`. Probing found the bugs in section 3.
4. Built `app/evaluation/` so the same scenarios become measurable, and ran it
   against both the untouched v0.8 commit and the result of this pass.

---

## 2. Current architecture (as implemented)

| Stage | Module(s) | Notes |
| :--- | :--- | :--- |
| Understanding | `understanding/memory_parser.py`, `entity_extractor.py`, `memory_entity_extractor.py`, `intent_detector.py`, `temporal_parser.py` | spaCy NER + a keyword entity list + keyword intent |
| Fact extraction | `knowledge/fact_extractor.py` | Dependency-parse → `KnowledgeFact(entity, attribute, value, temporal_state, …)` |
| Classification | `knowledge/classifier.py`, `contradiction_detector.py`, `processor.py` | Decision matrix over the **top-5 semantic candidates** |
| Decision | `decision/decision_engine.py` | `KnowledgeDecision` → `MemoryAction` |
| Evolution | `pipeline/memory_pipeline.py`, `service.py` | Supersession via `MemoryRelationship('superseded_by')`; contradiction via `is_contradicted` + archive |
| Graph | `graph/*` | **Process-local in-memory** graph, not persisted |
| Retrieval | `retrieval_service.py`, `ranking_service.py` | Semantic (pgvector) + ILIKE keyword + graph, weighted sum |
| Context | `context/*` | Evidence scoring → conflict resolution → ranking → diversity → budget → `ContextPackage` |

Facts are **not stored**: they are re-extracted from memory text by spaCy each
time a stage needs them.

---

## 3. Defects found and fixed in v0.9

Each fix has a regression test. The "Found by" column says how the defect was
discovered.

| # | Defect (v0.8 behavior) | Impact | Fix | Found by |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Cue matching used raw substrings: `"will"` matched *William*, `"moved"` matched *removed*, `"was"` matched *Washington* | Wrong temporal states and false transition evidence | `knowledge/temporal_cues.py`: one word-boundary-safe cue module replacing 4 duplicated lists | probing |
| 2 | Decay archived memories with `importance < 0.5` and `access_count < 3`, and it ran on reinforcement | Saying `"I live in Pune."` twice with the API's default `fact` category **archived the memory** | Decay demotes to `weak` only. Access counting never moves a memory out of `archived`. | probing |
| 3 | `Mumbai → Pune → Mumbai`: the exact-match path reinforced the archived Mumbai record, then Pune was archived too | **No current residence left** | `create_memory` prefers live records and reactivates an explicitly re-asserted contradicted memory. A memory is never contradicted by itself. | probing |
| 4 | Every attribute was treated as single-valued | `"I like tea."` archived `"I like coffee."` as a contradiction | `knowledge/attribute_schema.py`: only functional attributes (residence, employer, name, age, `favorite_*`, LOCATION/EMPLOYMENT/PROFILE) can be contradicted or superseded. Unknown attributes default to multi-valued. | probing |
| 5 | The value was the *last* object: `"I use my MacBook Air for development"` gave value `development` | A false contradiction archived `"I use a MacBook Air."` | Prefer the direct object | probing |
| 6 | `work` always mapped to employer | `"I work on my MacBook Air"` gave employer `MacBook Air` | `work at/for` → employer; `work on/with` → `work_on` / `work_with` | probing |
| 7 | `"I am planning to move to Bangalore."` gave attribute `plan`, temporal state CURRENT | Plans were not linked to residence and were not FUTURE | Intention verbs follow their complement and mark the fact FUTURE | benchmark |
| 8 | `"I used to live in Mumbai."` gave attribute `tool` | Historical residence invisible to residence queries | `used to <verb>` follows `<verb>` | benchmark |
| 9 | Current-query conflict resolution fell back to "newest `created_at` wins" | **`"Where do I live?"` returned the Bangalore plan.** A later-stated historical fact could displace the current one. | Explicit temporal priority per query intent, plus `superseded_by` lineage (loaded in one query) marking memories HISTORICAL | probing |
| 10 | Stored FUTURE plans could be contradicted or chosen as supersession targets | A current statement could erase a plan | Plans are exempt as contradiction and supersession targets | audit |
| 11 | Multi-valued facts collapsed to one per `(entity, attribute)` in context | `"What do I like?"` returned one preference | Domain key includes the value for multi-valued attributes | probing |
| 12 | Recency ties: rows written in one transaction share `now()` | "Most recent wins" became arbitrary | Tiebreak on the monotonic id | benchmark |

### Measured impact (same benchmark, same machine)

| Metric | v0.8 | v0.9 |
| :--- | ---: | ---: |
| Precision@1 | 0.500 | **1.000** |
| MRR | 0.571 | **1.000** |
| Recall@3 | 0.607 | **1.000** |
| nDCG@3 | 0.557 | **1.000** |
| Forbidden selection rate (e.g. a plan answering a current question) | 0.143 | **0.000** |
| Contradiction precision | 0.400 | **1.000** |
| Supersession precision / recall | 1.000 / 1.000 | 1.000 / 1.000 |
| Graph edge accuracy | 1.000 | 1.000 |
| Duplicate suppression accuracy | 0.000 | **1.000** |
| Fact extraction accuracy (20 labeled sentences) | 0.700 | **1.000** |
| Temporal classification accuracy | 0.900 | **1.000** |

The benchmark is small and was written alongside these fixes. The numbers
show that the targeted regressions are fixed. They do not measure general
quality. See `docs/EVALUATION.md`.

---

## 4. Documentation vs. implementation discrepancies

| Documentation claim | Implementation | Resolution |
| :--- | :--- | :--- |
| "Zero memory-content value checks (no coffee, espresso, Pune, Google, Python, MacBook …)" (`CURRENT_ARCHITECTURE.md`) | `understanding/memory_entity_extractor.py` contains a hard-coded keyword list (coffee, starbucks, python, tesla, macbook, cricket …). The list feeds graph nodes and query entities. `ranking_service.infer_query_category` has food/drink keywords. | **Open.** The fact extractor itself is value-free; the entity layer is not. Removing the list changes graph nodes that tests rely on, so it needs its own change (section 5). |
| `10_Memory_Decay.md`: decay archives | `09_Memory_Lifecycle.md`: archived = merged or contradicted | Code now follows 09. 10 is updated. |
| Graph described as the knowledge-graph layer | Process-local Python object, lost on restart. Graph retrieval is empty after a restart. | **Open** (section 5). |
| `automemory_os_backup.sql` | Schema predates `confidence`, `is_contradicted`, `contradicted_by_id` and `memory_relationships`. It also contains personal sample data. | **Open.** It is not a usable schema source; there are no migrations. |
| Agent `memories_used` | Comes from raw `retrieve_memories`, not from the ContextEngine selection that builds the prompt | **Open.** The two lists can disagree. |
| `GET /context` | Uses the legacy `context_service`, not `ContextEngine` | **Open.** |

---

## 5. Remaining gaps (not changed in this pass)

These are listed in the order recommended for implementation. Each answers the
brief's decision-rule questions briefly.

### 5.1 Test and database safety (do first)
- **Problem:** The test suite runs `DELETE FROM memories` against whatever
  `DATABASE_URL` points to. There are no migrations (`create_all` only), no FK
  on `contradicted_by_id`, no unique constraint on `(source, target, type)` in
  `memory_relationships`, and no vector index.
- **Owner:** `database.py`, a new `conftest.py`, Alembic under `services/memory-service/`.
- **Invariants at risk:** none if the baseline migration mirrors the current models exactly.
- **Tests:** `conftest.py` refuses to run unless the database name contains `test`. A migration round-trip test.
- **Migration path:** Alembic baseline revision equal to the current models, then additive revisions.

### 5.2 Provenance (first-class evidence)
- **Problem:** Nothing records where a memory came from. MERGE overwrites the
  canonical content with the newest phrasing and does not link archived
  duplicates to their canonical memory, so the original statements' lineage is lost.
- **Proposal:** A `memory_evidence` table (`memory_id` FK, `source_type`,
  `conversation_id`, `message_id`, `observed_at`, `extraction_method`,
  `extractor_version`, `confidence`, `raw_text`). A `merged_into`
  relationship type for merges. Every pipeline action appends evidence rather
  than overwriting it. Existing rows get no fabricated provenance:
  `source_type = 'legacy'`.
- **Invariants:** supersession ≠ contradiction is unchanged; merges keep the earliest timestamp.

### 5.3 Stored canonical facts
- **Problem:** Facts are re-parsed with spaCy up to about six times per
  candidate per request (classifier, contradiction detector, target selection,
  evidence evaluator, conflict resolver, diversity). Evolution only sees the
  **top-5 semantic neighbours**, so in a large store the conflicting
  same-attribute fact can be missed entirely.
- **Proposal:** A `knowledge_facts` table (`memory_id` FK, entity, attribute,
  value, temporal_state, cardinality, `valid_from`, `valid_to`, confidence),
  written by the pipeline and indexed on `(entity, attribute)`. Evolution
  candidates then come from a structural lookup plus semantic search.
  Retrieval gains exact `entity_match` / `attribute_match` signals.
  Superseded facts get `valid_to` instead of relying only on a relationship row.
- **Migration:** backfill by re-extracting existing memories; record the extractor version.

### 5.4 Entity layer and a persisted graph
- **Problem:** Graph search matches node labels by substring, so the query
  "rahul" returns memories about *Rahul Patel* and *Rahul Sharma*.
  `relationship_detector` applies one substring-detected relation to every
  entity in the sentence ("use" matches "because"). The graph is not persisted.
  The keyword entity list is domain hard-coding.
- **Proposal:** `entities` / `entity_aliases` tables with conservative
  resolution: an exact normalized name, or an explicit alias link, never
  embedding similarity alone. Graph edges derived from the stored fact
  attribute. Graph nodes and edges persisted in Postgres. Remove
  `MEMORY_KEYWORDS` once noun-chunk entities cover the tests.

### 5.5 Temporal events and uncertainty
- **Problem:** When a plan is fulfilled ("I will move to Bangalore" → "I moved
  to Bangalore"), the two memories are merged and the plan history is lost.
  There are no absolute or relative dates, and `ContextPackage` cannot say
  "insufficient evidence".
- **Proposal:** Add a relocation-style `events` table only where it fixes a
  measured failure. Add `uncertainty` to `ContextEvidence`: conflicting
  evidence, only historical or only future evidence for a current question.

### 5.6 Smaller items
- The lifecycle quirk: a reinforced memory with `access_count < 3` is set to
  `weak` (still retrievable). The weak/active semantics need a deliberate design.
- `GET /memory` mutates `access_count` on read.
- `duplicate_service.find_duplicate` prints to stdout.
- `services/memory-service/app.zip` (a 444 KB source snapshot) is committed.

---

## 6. Invariants protected by tests

- SUPERSESSION ≠ CONTRADICTION: superseded memories stay `active` and are not flagged as contradicted.
- FUTURE facts never answer CURRENT questions, and they are never contradicted or superseded by a different current value.
- Archiving happens only through merge or contradiction.
- Conservative entities: *Rahul Patel* ≠ *Rahul Sharma*, and "Rahul works at Google" creates no user edge.
- Multi-valued attributes coexist.
- The benchmark regression gate: `app/evaluation/test_benchmark.py`.
