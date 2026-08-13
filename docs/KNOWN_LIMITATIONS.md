# AutoMemory OS Known Limitations

## Overview

This document tracks known technical limitations of the current AutoMemory OS codebase.

---

## 1. Context Engine Score Representation

- `ContextCandidate.similarity` is retained for backward compatibility, but in the current ContextEngine pipeline it represents the final hybrid retrieval score returned by `retrieve_memories()`.

---

## 2. Fact Extraction & Reasoning

- Structured fact matching is used when `extract_fact()` succeeds in parsing structured entity-attribute-value facts.
- Unsupported natural-language facts fall back to generic semantic, entity, category, and temporal signals rather than domain-specific hardcoded rules.
- Richer natural-language fact understanding belongs to the future Memory Intelligence milestone.

---

## 3. Historical Candidate Retrieval Scope

- Historical mode can expose a broader archived candidate pool than strictly necessary; future retrieval improvements should make historical candidate discovery more targeted.

---

## 4. Process-Local In-Memory Knowledge Graph

- The Knowledge Graph state (`GraphRepository`) is stored in-memory and shared across `GraphService` instances within the same Python process.
- It is not persisted across server restarts or shared across multi-process cluster workers.
