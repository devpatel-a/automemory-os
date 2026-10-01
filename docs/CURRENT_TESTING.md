# Current Testing & Verification Reference

## Verified Test Suite Execution

The AutoMemory OS test suite validates system correctness across unit, integration, knowledge classification, temporal reasoning, graph consistency, and context optimization tests.

### Verification Command
```bash
cd services/memory-service
createdb automemory_os_test
export DATABASE_URL=postgresql://USER@HOST/automemory_os_test
export AUTOMEMORY_TEST_DATABASE=automemory_os_test
python -m pytest -q
```

> The suite deletes data, so it **refuses to run** (exit code 4) unless the
> database is named `<name>_test` (regex `^[a-z0-9_]+_test$`) **and**
> `AUTOMEMORY_TEST_DATABASE` equals that name (`app/testing_support.py`,
> `conftest.py`). A name that merely contains "test" is rejected. The
> destructive helpers (`reset_database()`, `prepare_test_schema()`) check this
> themselves. The session migrates the test database with `alembic upgrade head`.

### Final Verified Results (v0.8 Milestone)
- **Collected**: 116 tests
- **Passed**: 116 passed
- **Failed**: 0 failed
- **Skipped**: 0 skipped
- **Execution Time**: 20.17 seconds (environment baseline: 20.17s – 20.80s)
- **Success Rate**: 116 / 116 tests passed (100% test pass rate)

---

## Test Coverage Categories

1. **v0.7 Baseline & Regression Coverage**:
   - Zero product value hardcoding verification across coffee, city, company, programming, device, sport.
   - Object semantics (MacBook Air/computer/workstation → device vs Python/programming language → tool).
   - Non-user entity extraction (Rahul, brother).
   - Paragraph/paraphrase normalization.

2. **Temporal Reasoning & Fact States**:
   - Current fact state classification (`CURRENT`).
   - Historical fact state classification (`HISTORICAL`).
   - Future plan fact state classification (`FUTURE`).

3. **Supersession & Contradiction Separation**:
   - Fact transition supersession (`"I lived in Mumbai."` $\rightarrow$ `"I moved to Pune."`) preserving historical memories in DB (`state = "active"`, `is_contradicted = False`, linked via `MemoryRelationship("superseded_by")`).
   - Incompatible current assertion contradiction (`"I live in Mumbai."` $\rightarrow$ `"I live in Pune."` without transition phrasing) marking old memory `is_contradicted = True`, `state = "archived"`.

4. **Future Preservation & Non-Unique Values**:
   - Preservation of `CURRENT` facts alongside incoming `FUTURE` facts without premature supersession.
   - Non-unique value transition sequences (`Mumbai` $\rightarrow$ `Pune` $\rightarrow$ `Mumbai`) preserving object identity across distinct memory records.

5. **No-Longer Negation Semantics**:
   - Negated transition statements (`"I do not live in Mumbai anymore."`) updating existing facts to `HISTORICAL` without fabricating replacement values or storing fake `"unknown"` entries.

6. **Entity Relationships & Graph Safety**:
   - Explicit entity-to-user relationships (`"My friend Rahul works at Google."` $\rightarrow$ `user --friend_of--> rahul`).
   - Non-user subject relationship safety (`"Rahul works at Google."` $\rightarrow$ `rahul --works_at--> google`, preventing false `user --works_with--> rahul` edges).
   - Conservative entity resolution (`Rahul Patel` vs `Rahul Sharma`).

7. **Context Engine & Shared Graph Consistency**:
   - Temporal query intent preference (`CURRENT` queries prefer current facts; `HISTORICAL` queries prefer historical facts).
   - Process-shared thread-safe Knowledge Graph synchronization across independent service instances.

---

## v0.9 Results
- **Collected**: 149 tests (116 v0.8 baseline + 33 new).
- **Passed**: 149. **Failed**: 0.
- All 116 v0.8 tests are unchanged and pass.

New suites:
- `app/knowledge/test_temporal_cues.py`: word-boundary cue matching.
- `app/knowledge/test_fact_semantics.py`: value selection, cardinality, plans, multi-message evolution.
- `app/test_lifecycle_safety.py`: decay, re-assertion, self-contradiction.
- `app/context/test_query_aware_context.py`: query intent, lineage, structured evidence.
- `app/evaluation/test_benchmark.py`: metric unit tests and the benchmark regression gate (see `EVALUATION.md`).
- `app/test_config.py`: typed settings.

---

## v0.10 Results
- **Collected**: 254 tests. **Passed**: 254. **Failed**: 0.
- All v0.8/v0.9 tests pass with their assertions unchanged (their
  `clear_db()` helpers now delegate to the guarded `reset_database()`).

New suites:
- `app/test_startup_validation.py`: pinned spaCy model, actionable missing-model error, embedding dimension (384 valid, 768 rejected), live DB column dimension.
- `app/test_database_safety.py`: test-DB guard, including an end-to-end subprocess run against `automemory_os`.
- `app/test_migrations.py`: fresh-DB upgrade equals ORM metadata, downgrade/upgrade round trip, legacy `create_all` DB with anomalous data upgrades without loss, legacy provenance backfill.
- `app/test_database_constraints.py`: FK/unique/CHECK/cascade behavior enforced by PostgreSQL.
- `app/pipeline/test_pipeline_evolution.py`: one handler per decision; contradiction target resolved / resolved by wide search / unresolvable; multiple candidates; re-assertion; atomic rollback.
- `app/pipeline/test_concurrency.py`: concurrent duplicate insert, contradiction, re-assertion, relationship creation, plus a deterministic lost-update interleaving.
- `app/test_retrieval_lifecycle.py`, `app/test_retrieval_candidates.py`, `app/test_lexical_matching.py`.
- `app/test_agent_context_consistency.py`: agent `memories_used` == ContextPackage evidence.
- `app/graph/test_persistent_graph.py`: restart (new process), shared across services, entity safety, aliases, rollback, concurrency.
- `app/understanding/test_generic_entities.py`: unseen entities, no curated list.
- `app/test_admin_reads.py`, `app/provenance/test_provenance.py`, `app/knowledge/test_temporal_matrix.py`, `app/test_parse_cache.py`.

---

## v0.10.1 Results (pre-merge hardening)
- **Collected**: 285 tests. **Passed**: 285. **Failed**: 0. **Skipped**: 0 (two consecutive full runs).
- New: `app/pipeline/test_stale_target.py` (stale classification, bounded retry,
  phantom conflicting inserts, reflection lost update), `app/test_admin_mutations.py`
  (PUT), `app/test_delete_semantics.py` (archive vs. purge, FK integrity),
  stronger `app/test_database_safety.py`, 0005 checks in `app/test_migrations.py`.
