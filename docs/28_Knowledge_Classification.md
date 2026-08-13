# Knowledge Classification

## Purpose

The Knowledge Engine determines how incoming parsed knowledge interacts with existing stored memories.

---

## Current Implementation

Knowledge classification is implemented in [app/knowledge/classifier.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/classifier.py) via `classify_knowledge(parsed_memory, candidates)`.

### Decisions Supported (`KnowledgeDecision` Enum)

1. **`NEW`**: Unrelated to any existing memory (or no candidates found).
2. **`RELATED`**: Mentions shared entities or topics, but expresses distinct information (both memories remain active).
3. **`REINFORCEMENT`**: Exact or near-exact duplicate content strengthening an existing memory.
4. **`UPDATE`**: Fact value transition on the same entity and attribute (e.g. `"I work at Google."` → `"I work at Apple."`).
5. **`MERGE`**: Semantically equivalent information requiring consolidation into a single canonical memory.
6. **`CONTRADICTION`**: Direct conflict with existing active knowledge.

---

## Classification Rules & Evaluation Hierarchy

1. **Fact UPDATE Scan**: Scans candidates for normalized `same entity + same attribute + different value`. Returns `KnowledgeDecision.UPDATE`.
2. **Merge Equivalence Scan**: Evaluates candidates via `is_merge_equivalent(new_parsed, cand_mem, distance)`.
   - Rejects contradictions.
   - For structured facts: requires exact `entity`, `attribute`, AND `value` match.
   - For unstructured text: requires distance $< 0.08$ and Jaccard token overlap $\ge 0.35$.
   - Rejects category mismatches (e.g. `profile` vs `event`).
   - If exact text match: returns `REINFORCEMENT`; otherwise returns `MERGE`.
3. **Distance-Based Classification**:
   - Distance $< 0.10$: `REINFORCEMENT`
   - Distance $< 0.35$: `RELATED`
   - Distance $\ge 0.35$: `NEW`