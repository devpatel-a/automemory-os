# Knowledge Processor

## Purpose

The Knowledge Processor ([app/knowledge/processor.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/processor.py)) is the public API entry point for the Knowledge Engine.

---

## Responsibilities

1. Extract structured `KnowledgeFact` from incoming parsed memory via `extract_fact()`.
2. Evaluate candidates and classify knowledge via `classify_knowledge()`.
3. Check for contradictions via `detect_contradiction()`.
4. Construct and return a `KnowledgeResult` containing `decision` and `fact`.