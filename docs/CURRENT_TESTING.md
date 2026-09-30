# Current Testing & Verification Reference

## Verified Test Suite Execution

The AutoMemory OS test suite validates system correctness across unit, integration, knowledge classification, temporal reasoning, graph consistency, and context optimization tests.

### Verification Command
```bash
python -m pytest -q
```

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
