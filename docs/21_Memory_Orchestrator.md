# Memory Orchestrator

## Purpose

The `MemoryOrchestrator` ([app/orchestrator/memory_orchestrator.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/orchestrator/memory_orchestrator.py)) is an earlier standalone memory orchestration class.

---

## Responsibilities & Current Status

- **Responsibilities**: Generates embeddings (`generate_embedding`), performs semantic candidate search (`semantic_search`), detects exact/near-exact duplicates (`find_duplicate`), and constructs or strengthens memory objects.
- **Current Status**: `MemoryOrchestrator` remains present and functional in the codebase, backed by unit tests ([app/test_orchestrator.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/test_orchestrator.py)).
- **Relationship to MemoryPipeline**: `MemoryPipeline` ([app/pipeline/memory_pipeline.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/pipeline/memory_pipeline.py)) supersedes `MemoryOrchestrator` as the primary multi-tier entry point. While `MemoryOrchestrator` performs basic duplicate detection and memory creation, `MemoryPipeline` orchestrates full Knowledge Reasoning, Decision Engine evaluation, Memory Evolution (UPDATE, MERGE, CONTRADICTION), and Knowledge Graph building.