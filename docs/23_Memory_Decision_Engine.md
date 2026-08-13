# Memory Decision Engine

## Purpose

The Decision Engine ([app/decision/decision_engine.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/decision/decision_engine.py)) maps knowledge classification outputs (`KnowledgeDecision`) to concrete memory storage actions (`MemoryAction`).

---

## Current Supported Actions (`MemoryAction` Enum)

- `STORE`: Create new active memory.
- `REINFORCE`: Strengthen existing memory.
- `UPDATE`: Update existing memory in-place.
- `MERGE`: Merge redundant memory into canonical memory.
- `ARCHIVE`: Archive contradicted memory.
- `IGNORE`: Ignore incoming memory.
- `RELATED`: Store new memory and establish a relationship.

---

## Mapping Logic

| Input `KnowledgeDecision` | Evaluated `MemoryAction` |
| :--- | :--- |
| `KnowledgeDecision.NEW` | `MemoryAction.STORE` |
| `KnowledgeDecision.REINFORCE` | `MemoryAction.REINFORCE` |
| `KnowledgeDecision.UPDATE` | `MemoryAction.UPDATE` |
| `KnowledgeDecision.MERGE` | `MemoryAction.MERGE` |
| `KnowledgeDecision.CONTRADICTION` | `MemoryAction.ARCHIVE` |
| `KnowledgeDecision.RELATED` | `MemoryAction.RELATED` |
