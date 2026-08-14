# Known Limitations & System Boundaries

## Design Philosophy

AutoMemory OS intentionally relies on deterministic NLP algorithms, explicit dependency parsing, and structured database operations rather than non-deterministic Large Language Models (LLMs) or external cloud APIs. These operational boundaries define the scope of current capabilities.

---

## Technical & Architecture Boundaries

### 1. Deterministic Temporal Reasoning
- Temporal state classification (`CURRENT`, `HISTORICAL`, `FUTURE`) relies on spaCy verb tags, temporal indicators, and transition phrasing.
- Complex multi-event temporal narratives in a single sentence (e.g. `"Before living in Mumbai, I lived in Pune after moving from Delhi."`) are extracted as a primary fact rather than decomposed into multiple linked historical records.

### 2. Conservative Entity Resolution
- Entity resolution uses explicit entity/dependency structure and conservative contextual matching to avoid false merges.
- Similar names are not automatically treated as the same entity (`Rahul Patel` vs `Rahul Sharma`).
- Coreference resolution across separate distant conversations (e.g. resolving `"he"` to `Rahul` without explicit context) remains intentionally constrained.

### 3. Future Fact State Lifecycle
- Future plans (e.g. `"I will move to Bangalore next month."`) are stored with `temporal_state = "FUTURE"`.
- Future facts do not automatically transition to `CURRENT` based on system clock elapsed time without user input confirming the transition.

### 4. Graph Relationship Extraction Scope
- Knowledge graph edge extraction uses deterministic rule maps and POS structures.
- Implicit or nuanced interpersonal relationships unstated in text are not inferred or hallucinated.

### 5. Non-Probabilistic Storage
- AutoMemory OS uses discrete confidence scores and state flags rather than probabilistic graphical models.
