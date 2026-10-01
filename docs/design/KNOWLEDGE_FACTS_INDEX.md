# Design: `knowledge_facts` structural fact index

Status: **PR-1 implemented** (shadow index: written and checked, not read by
evolution). PR-2/PR-3 remain proposals. Baseline of the design: `main` @
`a1d5aaa` (v0.10.1). See §16 for what PR-1 implemented.
Scope: fix the documented evolution candidate-pool limitation
(`KNOWN_LIMITATIONS.md`, "Evolution candidate pool") and nothing else.

Every claim below was checked against the code at that commit. Items marked
**[verified]** were also reproduced on the approved test database with the
real pipeline.

---

## 1. Current architecture map for structured facts

### 1.1 Canonical representation (question A)

There is **no persisted structured fact**. The canonical representation is the
transient pydantic model `KnowledgeFact` (`app/knowledge/fact_models.py`):

| Field | Produced by extractor | Used at runtime |
| :--- | :--- | :--- |
| `entity` | raw subject text (`"user"`, `"Rahul Patel"`, `"brother"`) | yes |
| `attribute` | verb/noun map, `work_<prep>`, verb lemma, or `"general"` | yes |
| `value` | direct object, else last object/noun chunk; `"unknown"` placeholder | yes |
| `fact_type` | `LOCATION`, `EMPLOYMENT`, `PROFILE`, `DEVICE`, ... | yes (cardinality) |
| `temporal_state` | `CURRENT` / `HISTORICAL` / `FUTURE` (`UNKNOWN` is never produced) | yes |
| `is_negated` | any `neg` dependency or not/no/never/anymore | yes |
| `relationship_to_user` | friend/brother/... | graph only |
| `confidence` | 0.35 (placeholder) … 0.95 | evidence only |
| `temporal_info`, `evidence_count`, `contradiction_count`, `superseded_by_id` | defaults | **unused** |

**Source of truth today:** `memories.content` (current text) plus the
append-only `memory_evidence.raw_text` / `previous_text` (original statements).
A fact is a pure function of `(text, extractor rules, spaCy model)`.

### 1.2 Where `(entity, attribute, value, temporal_state, negation)` is derived (question B)

The only producer is `extract_fact(ParsedMemory)` in
`app/knowledge/fact_extractor.py`. It returns **zero or one** fact per text.
Derived semantics layered on top of it:

| Concept | Where | Notes |
| :--- | :--- | :--- |
| Cardinality | `attribute_schema.is_single_valued(fact)` | depends on `attribute` **and** `fact_type` |
| Context domain key | `attribute_schema.fact_domain_key(fact)` → tuple | `(entity, attribute[, value])` |
| Lock domain key | `service.fact_domain_key(fact)` → string | `fact-domain:entity\|attribute` (**name collision** with the above) |
| Effective temporal state | `conflict_resolver.effective_temporal_state` | extracted state, overridden to HISTORICAL by `superseded_by` / `fulfilled_by` lineage |
| Lifecycle | `memories.state`, `is_contradicted`, `contradicted_by_id` | never part of the fact |
| Key normalization | `entity.strip().lower()` etc. in classifier/detector | **differs** from the graph's `normalize_entity_name` (strips determiners and possessives) |

### 1.3 Who re-parses raw memory text (question C)

Every consumer re-derives the fact from text (the spaCy `Doc` is cached by
`app/nlp.parse_text`; `KnowledgeFact` construction is not):

| Consumer | File | Purpose |
| :--- | :--- | :--- |
| Domain lock | `pipeline/memory_pipeline.py:169` | incoming fact → advisory lock key |
| Classification loop | `knowledge/classifier.py:129` | each **top-5 candidate** |
| Merge equivalence | `knowledge/classifier.py:32-33` | candidate vs. incoming |
| Contradiction detector | `knowledge/contradiction_detector.py:28-29` | safety net over top-5 |
| Plan fulfilment | `pipeline/memory_pipeline.py:346` | FUTURE plans among top-5 |
| Graph persistence | `graph/graph_service.py:28`, `graph/relationship_detector.py:46` | subject/value entities |
| Admin PUT | `service.py:338,359` | old/new lock keys, evidence confidence |
| Context | `context/conflict_resolver.py:101`, `evidence_evaluator.py:43-46`, `diversity.py:54`, `query_intent.py:42` | ranking and conflict resolution |

### 1.4 Evolution data flow today

```
process(text)
  parse_memory, generate_embedding
  ┌ transaction (retry ≤ 3 on EvolutionConflict / 40P01 / 40001)
  │ lock_fact_domains([extract_fact(text)])           advisory lock (entity|attribute)
  │ candidates = semantic_search(limit=5)             ← the ONLY candidate source
  │ snapshot versions; historical = lineage lookup
  │ process_knowledge(text, candidates)               classifier + detector, both over the 5
  │ handler(decision, target)                         _lock_live: FOR UPDATE + version/state/lineage check
  │ _link_fulfilled_plans(candidates)                 again only over the 5
  │ evidence row; graph rows
  └ commit
```

---

## 2. Exact failure mode of the top-5 approach

1. The candidate pool is `semantic_search(content, limit=5)`, ordered by cosine
   distance of the **whole sentence**. Topical sentences that share the *value*
   ("Pune") are closer than the conflicting fact that shares the *attribute*
   ("I live in Mumbai.").
2. The classifier's conflict loop, the processor's contradiction safety net,
   merge detection and plan fulfilment all iterate **only** those 5.
3. The 50-candidate "wide fallback" (`_find_conflicting_memory`) runs only when
   the decision is CONTRADICTION **without** a target. Both CONTRADICTION paths
   (`assess_knowledge` and the processor safety net) always set
   `target_memory_id` from a top-5 candidate, so in production the fallback is
   **unreachable**. Only `test_contradiction_target_recovered_by_wide_search`
   reaches it, by monkeypatching the classifier. It is not a mitigation.

**[verified]** With "I live in Mumbai." and 14 Pune-related statements stored,
"I live in Mumbai." ranks **9th** for "I live in Pune.". Processing
"I live in Pune." then:
- misses the conflict: **both residences remain live** (invariant "≤ 1 live
  current value per single-valued domain" broken);
- decides **MERGE** with "My parents live near Pune." (see §2.1) and
  overwrites that memory's text with "I live in Pune." (the original survives
  only in `memory_evidence.raw_text`).

The same blindness affects supersession targets, negation ("no longer"),
plan fulfilment and same-value reinforcement/merge.

### 2.1 Pre-existing extraction defects the index would amplify **[verified]**

| Input | Extracted | Consequence |
| :--- | :--- | :--- |
| "My parents live near Pune." | `(user, residence, Pune)` | Possessive subjects not in `RELATION_NOUNS` collapse to `user`, attributing third-party facts to the user. |
| "I live there." | `(user, residence, "unknown", conf 0.35)` | The placeholder value is treated as a real value. **Today**, "I live there." archived "I live in Pune." as contradicted. |

Today both are limited to the semantic neighbourhood. A global
`(entity, attribute)` lookup would make them **guaranteed** across the whole
store. They must be fixed, or explicitly excluded from conflict participation,
**before** the index is allowed to influence decisions (§12).

---

## 3. Proposed `knowledge_facts` data model

One table, a **derived lookup index**, rebuildable from `memories.content`.

```
knowledge_facts
  memory_id          INTEGER  PK, FK -> memories(id) ON DELETE CASCADE
  entity_key         VARCHAR(255) NOT NULL   -- normalized fact.entity
  attribute_key      VARCHAR(128) NOT NULL   -- normalized fact.attribute
  value_key          VARCHAR(255) NOT NULL   -- normalized fact.value
  value_text         TEXT NOT NULL           -- fact.value as extracted (display/debug)
  fact_type          VARCHAR(32)  NOT NULL
  single_valued      BOOLEAN NOT NULL        -- is_single_valued(fact) at extraction time
  temporal_state     VARCHAR(16)  NOT NULL   -- EXTRACTED state, never the effective one
  is_negated         BOOLEAN NOT NULL
  is_placeholder     BOOLEAN NOT NULL        -- value was a placeholder ("unknown", "this", ...)
  confidence         DOUBLE PRECISION NOT NULL
  content_sha256     CHAR(64) NOT NULL       -- hash of memories.content the row was derived from
  extractor_version  VARCHAR(32) NOT NULL    -- provenance.models.EXTRACTOR_VERSION
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
```

**Deliberately absent:**
- **Lifecycle** (`state`, `is_contradicted`) and **effective temporal state**
  (superseded/fulfilled). These stay in `memories` and `memory_relationships`
  and are read by join. Copying them would create a second source of truth that
  every lifecycle path (archive, purge, contradiction, supersession, fulfilment,
  reactivation, merge, admin edit) would have to keep in sync.
- `valid_from` / `valid_to` (proposed in `ARCHITECTURE_ASSESSMENT.md` §5.3).
  Temporal validity is already expressed by lineage; duplicating it here has
  the same drift problem. This is a deliberate change to that earlier proposal.
- `evidence_count`, `contradiction_count`, `superseded_by_id`. These are
  unused at runtime (§1.1).

### One memory → how many facts? (question E)

**Zero or one row, keyed by `memory_id`.** `extract_fact` returns at most one
fact, and multi-event sentences are a documented limitation. A composite key
`(memory_id, ordinal)` would be speculative. If fact decomposition is ever
added, migrating the PK to `(memory_id, ordinal)` is a small, additive change.
Memories with no fact or no attribute get **no row**.

---

## 4. Ownership / source-of-truth semantics (questions D, G)

| Concern | Source of truth | `knowledge_facts` role |
| :--- | :--- | :--- |
| What was said | `memory_evidence.raw_text` (append-only) | none |
| What a memory currently says | `memories.content` | derived snapshot of its fact |
| Lifecycle | `memories.state`, `is_contradicted`, `contradicted_by_id` | none (join) |
| Temporal lineage | `memory_relationships` | none (join) |
| Graph identity | `entities` / `entity_aliases` | none in v1 (§7) |
| "Which memories assert something about (entity, attribute)?" | — | **the index answers this** |

**G:** fact rows are a **current-content index**, not a history. History and
audit live in `memory_evidence` (raw text, previous text, extractor version,
decision, reason codes). When a memory's text changes (merge canonical, admin
PUT), its fact row is **rewritten**. Rows exist for archived and historical
memories too, because lifecycle is filtered at query time.

### Invariants (question D)

- **I1 (derivation):** for every row,
  `row == derive(memories.content)` under `extractor_version`, witnessed by
  `content_sha256 = sha256(memories.content)`.
- **I2 (completeness):** every memory written by `MemoryPipeline` or the admin
  `PUT` whose text yields a fact with an attribute has exactly one row, written
  **in the same transaction** as the content change.
- **I3 (monotonic safety):** the index may only **add** evolution candidates.
  It never removes semantic candidates and never decides anything itself, so a
  missing or stale row degrades to today's behaviour, never worse.
- **I4 (no duplicated state):** no lifecycle or lineage columns.
- **I5 (domain consistency):** lookups for an incoming fact happen **inside**
  the existing `lock_fact_domains` advisory lock, using the same key
  normalization as the lock and the classifier comparison.
- **I6 (cascade):** a purged memory leaves no fact row (FK `ON DELETE CASCADE`).

Not enforceable as a database constraint (and stated honestly):
"≤ 1 live, non-historical CURRENT fact per single-valued domain". Liveness spans
`memories` and `memory_relationships`. It stays an application invariant,
enforced by evolution under the domain lock and audited by a checker (§8).

---

## 5. Indexes and constraints (question H)

| Object | Purpose |
| :--- | :--- |
| `PRIMARY KEY (memory_id)` | 0..1 row per memory; idempotent upsert target |
| `FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE` | I6 |
| `INDEX ix_knowledge_facts_domain_value (entity_key, attribute_key, value_key)` | **one** B-tree serving both lookups: by `(entity, attribute)` as a prefix (conflicts), and by `(entity, attribute, value)` (merge, reinforcement, plan fulfilment) |
| `CHECK (temporal_state IN ('CURRENT','HISTORICAL','FUTURE','UNKNOWN'))` | domain validity |
| `CHECK (entity_key <> '' AND attribute_key <> '')` | no empty keys |
| `CHECK (char_length(content_sha256) = 64)` | I1 witness well-formed |

**Not needed:**
- No uniqueness on `(entity, attribute, value)`: duplicates are legitimate
  (archived, historical, multi-valued).
- No partial index on lifecycle: lifecycle is not in the table.
- No GIN or trigram index: lookups are exact-key only.

The join filter (`memories.state <> 'archived'`) uses the existing
`ix_memories_state` / primary key.

---

## 6. Interaction with MemoryPipeline classification (questions K, L)

### 6.1 Candidate construction (PR-3, not PR-1)

Inside `_evolve`, **after** `lock_fact_domains` (unchanged), add a structural
lookup and take the **union** with the semantic candidates:

```
fact = extract_fact(parsed)                      # already computed for the lock
semantic = semantic_search(limit=5)              # unchanged
structural = []
if fact and fact.attribute and not placeholder:
    if single_valued(fact):
        structural = live memories with (entity_key, attribute_key)      # conflicts, supersession, negation
    else:
        structural = live memories with (entity_key, attribute_key, value_key)  # merge / reinforce
    plans = live memories with (entity_key, attribute_key, value_key) and temporal_state='FUTURE'
    ORDER BY memory_id DESC LIMIT STRUCTURAL_LIMIT (e.g. 20); log a reason code if truncated
candidates = semantic + [m for m in structural+plans if m.id not in semantic]   # semantic order first
```

- "Live" means `memories.state <> 'archived'`. Historical lineage is still
  computed by `historical_memory_ids` over the union, exactly as today.
- Structural candidates carry `distance = None`. In the classifier, distance
  only matters in the non-fact merge fallback and in the distance-based
  REINFORCEMENT/RELATED tail. Both use `live[0]`, which stays the best
  **semantic** candidate because semantic candidates come first. **Ambiguity
  to settle in PR-3:** `assess_knowledge` returns on the *first* conflicting
  candidate. With the union, ordering decides which conflicting memory is
  targeted when legacy data already holds several. Proposal: semantic order,
  then structural by `memory_id DESC` (most recent assertion).

### 6.2 Safety model (unchanged)

- The domain advisory lock is taken **before** the lookup. No pipeline
  statement in the same domain can change the index or the memories it points
  to between lookup and write. Admin `PUT` takes the same domain locks for its
  old and new facts.
- Archive and purge take only row locks. If one lands between lookup and write,
  the existing `_lock_live` check (version, state and lineage under
  `FOR UPDATE`) raises `EvolutionConflict` and the evolution is reclassified
  from fresh state, bounded by `MAX_ATTEMPTS`. Structural candidates are loaded
  as `Memory` rows and their versions are added to `_classified_versions`, so
  nothing new is needed.
- Writing a fact row takes an FK `KEY SHARE` lock on its memory. The only
  writer of a memory's fact row is the transaction that changed that memory's
  content, and it already holds that row's `FOR UPDATE` lock or created the
  row. So no new lock-ordering edge is introduced.

### 6.3 Retrieval stays semantic (L)

The index is used **only** for evolution candidate generation. Hybrid
retrieval, context assembly and ranking are untouched. The following stay
semantic or lexical by design:
- memories without an attribute;
- RELATED / near-duplicate decisions;
- the query-time context pipeline.

---

## 7. Normalization and aliases (question I)

- **Key normalization must equal the classifier's equality**, or be coarser.
  The index is a candidate generator: being coarser only adds candidates that
  the classifier then rejects. Being stricter would silently miss them. v1:
  use exactly the classifier's `str.strip().lower()` for entity, attribute and
  value. Introduce **one** helper, `normalize_fact_key()`, used by the
  classifier, the detector, the lock key and the index, so the rule cannot
  diverge again. Any later change to it requires a reindex.
- **Aliases: not in v1.** The classifier compares raw entity strings and
  ignores `entity_aliases`. If only the index resolved aliases, it would return
  candidates the classifier then treats as different entities: no effect, only
  cost. Alias-aware evolution needs the classifier to compare resolved entity
  ids. That is a separate, later decision (add `entity_id` FK then).
- **Graph vs. fact keys diverge today** (`normalize_entity_name` strips
  "the/my", the fact path does not). This is documented, not changed by this
  work.

## 8. Negation, plans, placeholders (question J)

- **Negated facts** are stored with `is_negated = true` and their extracted
  temporal state ("I do not live in Mumbai anymore" → `HISTORICAL`, value
  `mumbai`). They are looked up like any other row; Rule G (negation of the
  same value → SUPERSESSION) then finds its target anywhere in the domain.
- **Future plans** are stored with `temporal_state = 'FUTURE'`. The classifier
  already never contradicts or supersedes them. Fulfilment uses the
  `(entity, attribute, value)` lookup filtered to `FUTURE`.
- **Placeholders** ("unknown", "this", "it", ...) are stored with
  `is_placeholder = true`, but **excluded from structural lookup** on both
  sides. PR-2 must additionally stop placeholder facts from contradicting real
  values (§2.1), independent of the index.

## 9. Lifecycle behavior (question F)

| Event | Effect on `knowledge_facts` | Why |
| :--- | :--- | :--- |
| NEW / RELATED store | insert row for the new memory | I2 |
| REINFORCEMENT, reactivation (exact re-assertion) | none (content unchanged; hash still matches) | I1 |
| SUPERSESSION | insert row for the new memory; old row unchanged | effective HISTORICAL comes from lineage |
| CONTRADICTION | insert row for the incoming memory; target row unchanged | target is `archived` → excluded by the join, retained for audit/reactivation |
| MERGE | canonical row **rewritten** (its text becomes the merged statement); archived duplicates keep their rows | rows follow `memories.content` |
| Fulfilled plan | none | `fulfilled_by` lineage marks it historical |
| Archive (DELETE default) | none | excluded by the join; reversible |
| Admin PUT | row rewritten (or deleted if the new text yields no fact), same transaction | I1/I2 |
| Purge | row deleted by `ON DELETE CASCADE` | I6 |
| Extractor change | rows with an old `extractor_version` are stale until reindexed | `extractor_version` + hash |

Write path: a single `sync_memory_fact(db, memory)`, an idempotent upsert keyed
by `memory_id`, or a delete when there is no fact. It is called in exactly two
places:
1. `MemoryPipeline._evolve` for `evolution.memory`, after the handler. This
   covers store, supersession, contradiction, merge canonical and
   reactivation, because every handler returns the memory whose content it
   wrote.
2. `service.update_memory` (admin PUT).

Memories inserted by other paths (direct ORM inserts in tests, legacy rows)
simply have no row until the backfill runs. By I3 that is safe.

## 10. Migration / backfill (question M)

1. **`0006_knowledge_facts` (schema only):** creates the table, the FK, the
   index and the CHECKs. No data movement. Running spaCy inside Alembic would
   make the migration slow, model-dependent and hard to roll back. Downgrade
   drops the table; it holds only derived data.
2. **Backfill command** (`python -m app.knowledge.fact_index reindex`):
   - batched by `memory_id`;
   - **idempotent and resumable**: it processes memories with no row, a hash
     mismatch, or an old `extractor_version`;
   - per memory, it locks the row (`FOR UPDATE SKIP LOCKED`; skipped rows are
     picked up next pass), recomputes the fact, and upserts in a short
     transaction;
   - safe to run while the service is live: a pipeline write of the same
     memory holds the row lock, and the hash witness makes a late upsert from
     stale text detectable;
   - non-destructive: it never touches `memories`, evidence or lineage.
3. **Checker** (`... fact_index check`): reports missing rows, hash/version
   mismatches, and single-valued domains with more than one live,
   non-historical CURRENT fact (legacy inconsistencies the old top-5 misses
   may already have created). Report only; it never "fixes" data.
4. Enable the read path (PR-3) only after the checker reports full coverage
   on the target database. By I3 it is safe even before that, just less
   effective.

## 11. Test plan (question N)

**PR-1 (index, no read path):**
- migration: fresh upgrade matches the ORM metadata; downgrade/upgrade round
  trip; legacy DB (existing tests extended); FK cascade on purge.
- write-path parity, one test per event in §9: row equals `derive(content)`;
  hash and version recorded; MERGE rewrites the canonical row; admin PUT
  rewrites or deletes; contradiction keeps the target row; archive keeps the
  row; purge deletes it.
- atomicity: a failure after the handler (existing monkeypatch tests) leaves
  no fact row; a PUT failure leaves the old row.
- backfill: idempotent (two runs → same rows), resumable, legacy rows, skips
  locked rows, does not modify `memories`.
- checker: detects a missing row, a hash mismatch, and a deliberately inserted
  pair of conflicting live CURRENT facts.
- **behaviour parity:** the full existing suite and the benchmark unchanged
  (PR-1 must not change a single decision).

**PR-2 (extraction prerequisites):**
- "My parents live near Pune." no longer yields `entity = user`.
- "I live there." never contradicts or supersedes a real value.
- Existing extraction/benchmark tests unchanged.

**PR-3 (read path):**
- the §2 reproduction (conflict ranked 9th) → CONTRADICTION of "I live in
  Mumbai.", exactly one live residence, no MERGE into an unrelated memory;
- supersession, negation and plan fulfilment beyond the top 5;
- multi-valued domains use an exact-value lookup (bounded) and coexist;
- archived and historical structural candidates are excluded;
- stale target: archive or admin PUT of a structural candidate between lookup
  and lock → `EvolutionConflict`, reclassified (reuse the
  `test_stale_target.py` pattern);
- concurrency: two conflicting statements whose existing conflict is outside
  the top 5, processed concurrently → exactly one live current value, no
  self-contradiction;
- `STRUCTURAL_LIMIT` truncation emits a reason code;
- benchmark: add a "large distractor set" scenario to the regression gate.

## 12. Files that would change

| PR | Files |
| :--- | :--- |
| PR-1 | `alembic/versions/0006_knowledge_facts.py` (new); `app/knowledge/fact_index.py` (new: model, `normalize_fact_key`, `derive_fact_row`, `sync_memory_fact`, reindex/check CLI); `app/pipeline/memory_pipeline.py` (one `sync_memory_fact` call); `app/service.py` (one call in `update_memory`); `alembic/env.py`, `app/testing_support.py` (register model); tests; `docs/` |
| PR-2 | `app/knowledge/fact_extractor.py` (possessive-subject entity, placeholder flag); `app/knowledge/classifier.py`, `contradiction_detector.py` (placeholders never conflict); tests |
| PR-3 | `app/pipeline/memory_pipeline.py` (structural lookup + union, versions snapshot); `app/knowledge/fact_index.py` (lookup query); possibly remove the unreachable wide fallback (separate commit, with its test updated and justified); tests; benchmark scenario; `docs/KNOWN_LIMITATIONS.md` |

## 13. Risks, trade-offs, rejected alternatives

**Risks**
- *Amplified extraction errors* (§2.1). This is the main risk, so PR-2 must
  land before PR-3.
- *Index drift* if a future code path changes `memories.content` without
  `sync_memory_fact`. Mitigated by I3 (degrades safely), the hash witness and
  the checker. A test asserts that the only content writers are the two known
  call sites.
- *Large multi-valued domains* (e.g. `user|preference`). Mitigated by the
  exact-value lookup for multi-valued facts and `STRUCTURAL_LIMIT`.
- *Write cost:* one extra upsert per statement, in the same transaction.
- *Legacy inconsistencies* (several live current values) become visible to
  classification; PR-3 targets one per statement (§6.1 ambiguity).

**Rejected alternatives**
- *Raise `CANDIDATE_LIMIT` (e.g. 50).* This is still probabilistic: it fails
  as soon as a domain has more topical neighbours than the limit, and costs
  ~10x the classifier work per statement.
- *Use the existing wide search more often.* Same probabilistic flaw; it is
  also currently unreachable (§2).
- *Query `memory_entities` / the graph for candidates.* The graph links
  entities, not `(entity, attribute)` facts. Its keys use a different
  normalization, and its edges come from lemma heuristics, not from
  `extract_fact`. It would be coarser in the wrong dimension.
- *Store lifecycle / `is_current` in the fact table, plus a partial unique
  index enforcing "one current value".* Attractive, but it duplicates state
  owned by `memories` and `memory_relationships` and needs every lifecycle
  path to update it transactionally. Deferred until the derived index has
  proven itself.
- *Database trigger to maintain rows.* Extraction needs spaCy and cannot run
  in PostgreSQL.
- *Make the index the source of truth (facts first, text second).* This is a
  redesign; out of scope.

## 14. Staged plan

| Stage | Content | Behaviour change |
| :--- | :--- | :--- |
| **PR-1** | Table + migration, write path (2 call sites), backfill + checker CLI, tests | **none** (shadow index) |
| PR-2 | Fix possessive-subject entity resolution; placeholder values never conflict; shared `normalize_fact_key` | yes (bug fixes, with tests) |
| PR-3 | Structural lookup ∪ semantic candidates in `_evolve`; benchmark scenario | yes (the actual fix) |
| PR-4 (optional) | Alias-aware keys via `entity_id` | yes |

---

## 15. Recommendation: first PR only

**PR-1: "knowledge_facts shadow index" (no behaviour change).**

In scope:
1. Migration `0006_knowledge_facts`: the table, PK/FK cascade, the composite
   index and the CHECKs exactly as in §3/§5. Schema only, no data migration.
2. `app/knowledge/fact_index.py`:
   - the ORM model;
   - `derive_fact_row(content)` and `sync_memory_fact(db, memory)` (idempotent
     upsert, or delete when there is no fact);
   - `reindex` and `check` CLI commands.
3. Exactly two write call sites: `MemoryPipeline._evolve` (for
   `evolution.memory`, before evidence and graph, in the same transaction)
   and `service.update_memory`.
4. Tests from §11 "PR-1", including **behaviour parity**: the full existing
   suite and the benchmark unchanged.
5. Docs: this design, plus one line in `KNOWN_LIMITATIONS.md` ("index
   populated, not yet used for classification").

Out of scope:
- any read of `knowledge_facts` during classification or retrieval;
- extractor changes (PR-2);
- alias resolution;
- removing the unreachable wide fallback;
- changing `CANDIDATE_LIMIT`;
- lifecycle columns;
- any API change.

Acceptance criteria:
- `alembic upgrade head` works on fresh and legacy databases, and downgrade
  works;
- the existing suite passes unchanged and benchmark metrics are identical;
- every pipeline/PUT-written memory with a fact has a matching row
  (`content_sha256`);
- the backfill is idempotent;
- the checker on the test database reports zero missing or stale rows after
  the backfill.

---

## 16. PR-1 as implemented

- Schema: `alembic/versions/0006_knowledge_facts.py` and
  `app/knowledge/fact_index_model.py`, exactly as §3/§5.
- Derivation and sync: `app/knowledge/fact_index.py`
  (`derive_fact_row`, `sync_memory_fact`). Two call sites, each inside the
  existing transaction: `MemoryPipeline._evolve` (for `evolution.memory`,
  after the handler) and `service.update_memory` (admin PUT). Purge relies on
  `ON DELETE CASCADE`.
- Backfill and rebuild: `python -m app.knowledge.fact_index reindex [--all]`
  and `... check`. The migration is schema-only; no NLP runs inside Alembic.
- Clarifications made while implementing, none of them new semantics:
  - The extractor's own markers are now named constants in
    `fact_extractor.py` (`PLACEHOLDER_VALUES`, `MISSING_VALUE`,
    `NO_ATTRIBUTE`). Extraction behaviour is unchanged.
  - The `NO_ATTRIBUTE` marker (`"general"`) counts as "no attribute", so such
    memories get no row.
  - If a derived key would exceed its column length, the memory gets no row.
    Keys are never truncated, and the rule is deterministic, so rebuilds give
    identical results.
  - `lookup_fact_rows` (tests and the next stage only) excludes placeholder
    rows unless explicitly asked.
- Not consulted: tests assert the pipeline only INSERTs/DELETEs
  `knowledge_facts`, and that decisions are identical with a clean, an empty
  and a deliberately poisoned index.
