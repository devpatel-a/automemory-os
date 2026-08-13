# Confidence Engine

## Purpose

The Confidence Engine ([app/knowledge/confidence_engine.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/confidence_engine.py)) and Memory Evolution Engine ([app/service.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/service.py)) track and calculate belief confidence scores for facts and stored memories.

---

## Verified Numeric Confidence Rules

The following numeric confidence rules are implemented in source code:

1. **Initial Confidence**:
   - Facts and memories default to a baseline confidence $[0.0, 1.0]$ (typically `1.0`).
2. **Reinforcement Increment**:
   - `reinforce_fact()` & `reinforce_existing_memory()`: Increments confidence by `+0.10` (`min(1.0, confidence + 0.10)`).
3. **Fact UPDATE Increment**:
   - `update_existing_fact_memory()`: Increments confidence by `+0.05` (`min(1.0, confidence + 0.05)`).
4. **MERGE Preservation & Boost**:
   - `merge_existing_memories()`: Preserves the maximum confidence among merged candidate memories, then applies a `+0.05` boost (`min(1.0, max(candidate_confidences) + 0.05)`).
5. **Contradiction Penalty / Reduction**:
   - `contradict_fact()`: Decreases fact confidence by `-0.20` (`max(0.0, confidence - 0.20)`).
   - `contradict_existing_memory()`: Decreases target memory confidence by `-0.20` (`max(0.0, confidence - 0.20)`) prior to archiving.