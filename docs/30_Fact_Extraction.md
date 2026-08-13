# Fact Extraction

## Purpose

The Fact Extractor ([app/knowledge/fact_extractor.py](file:///Users/devpatel/Desktop/AutoMemory%20OS/services/memory-service/app/knowledge/fact_extractor.py)) parses structured memory representations into atomic `KnowledgeFact` objects.

---

## Current Fact Schema

A `KnowledgeFact` contains:
- `entity`: Lowercase normalized subject entity (e.g. `"user"`).
- `attribute`: Lowercase normalized attribute (e.g. `"residence"`, `"workplace"`).
- `value`: Lowercase normalized fact value (e.g. `"pune"`, `"google"`).

---

## Pattern Extraction Support

Rule-based pattern matching extracts facts from statements such as:
- `"I live in Pune."` → `entity="user"`, `attribute="residence"`, `value="pune"`
- `"I work at Google."` → `entity="user"`, `attribute="workplace"`, `value="google"`
- `"My name is Alex."` → `entity="user"`, `attribute="name"`, `value="alex"`