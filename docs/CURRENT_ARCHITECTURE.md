# Current Architecture Reference

## Overview

AutoMemory OS is an AI memory system currently implemented within:

`services/memory-service/`

This document describes the current repository architecture rather than
the broader future product vision.

---

# Current Modular Architecture

```text
User Input / API Request
        ↓
1. Understanding Engine
   app/understanding/
        ↓
2. Candidate Retrieval
   Semantic + Keyword + Graph
        ↓
3. Knowledge Engine
   app/knowledge/
        ↓
4. Decision Engine
   app/decision/
        ↓
5. Memory Evolution
   app/service.py
        ↓
6. Knowledge Graph
   app/graph/
        ↓
7. Context Engine
   app/context/