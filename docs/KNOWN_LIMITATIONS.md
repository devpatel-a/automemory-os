# AutoMemory OS Known Limitations

## Overview

This document tracks known technical boundaries and architectural limitations of the current AutoMemory OS codebase.

---

## 1. Single-Fact Contract for Compound Temporal Sentences

- Fact extraction in `app/knowledge/fact_extractor.py` represents one primary structured `KnowledgeFact` per input sentence.
- Compound sentences containing multiple temporal facts (e.g. `"I lived in Mumbai before moving to Pune."`) are not yet decomposed into separate structured facts. The current extractor produces a single primary fact with coarse temporal information.

---

## 2. Deterministic Fact Extraction vs LLM-Powered Reasoning

- Fact extraction is 100% deterministic and inspectable, using spaCy dependency parsing, POS tags, noun chunks, and centralized canonical attribute normalization (`VERB_ATTRIBUTE_MAP` and `NOUN_ATTRIBUTE_MAP`).
- It does not use LLM prompt-based extraction or generative AI models.

---

## 3. Deterministic Confidence Model

- Confidence scoring is calculated deterministically (`0.35` for ambiguous demonstrative pronouns, `0.60` base, up to `0.95` for complete multi-token facts).
- It is not a probabilistic or machine-learned confidence model.

---

## 4. Conservative Entity Resolution Scope

- User self-references (`I`, `me`, `my`, `myself`) normalize to `user`.
- Non-user subjects (`Rahul`, `brother`, `friend`) extract the grammatical subject entity cleanly.
- Entity resolution is conservative and does not connect to an external universal entity knowledge base. Advanced cross-document entity disambiguation remains future work.

---

## 5. Conservative Object Semantic Classification

- Object semantics classification for `"use"` is conservative: if the system cannot confidently classify `DEVICE` vs `TOOL`/`OTHER` via POS and noun chunk head structure, it defaults to `tool`/`OTHER`.
- The fact extractor contains zero product-value keywords (no MacBook, iPhone, iPad, Python, Pune, Google, etc.).
- Legacy `MEMORY_KEYWORDS` in `app/understanding/memory_entity_extractor.py` is maintained for understanding compatibility but is not used by `extract_fact()`.

---

## 6. Future Work: Advanced Temporal Reasoning

- Multi-event temporal decomposition and timeline reasoning across multiple temporal states remain future work.

---

## 7. Future Work: Advanced Semantic & Entity Resolution

- Multi-tenant entity disambiguation, cross-entity graph resolution, and multi-clause multi-fact extraction remain future work.

---

## 8. Process-Local In-Memory Knowledge Graph

- The Knowledge Graph state (`GraphRepository`) is stored in-memory and shared across `GraphService` instances within the same Python process.
- It is not persisted across server restarts or shared across multi-process cluster workers.
