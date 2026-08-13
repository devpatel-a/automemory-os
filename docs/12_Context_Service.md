# Context Service

> [!NOTE]
> **Historical / Foundational Document**  
> This document describes an earlier Context Service implementation. The current Context Engine implementation is documented in [CURRENT_CONTEXT_ENGINE.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_CONTEXT_ENGINE.md).

---

## Historical Overview

The Context Service was responsible for selecting memories that will be used by the AI.

### Early Responsibilities

- Read memories
- Filter archived memories
- Rank by importance
- Return the top K memories

The Context Service did not:
- Create memories
- Update memories
- Delete memories

---

## Historical Roadmap

Earlier specifications planned:
- Semantic search
- Conversation awareness
- Token budgeting
- Context compression
- Prompt construction

*(Note: Semantic search, token budgeting, candidate ranking, and prompt construction are now fully implemented in [CURRENT_CONTEXT_ENGINE.md](file:///Users/devpatel/Desktop/AutoMemory%20OS/docs/CURRENT_CONTEXT_ENGINE.md).)*