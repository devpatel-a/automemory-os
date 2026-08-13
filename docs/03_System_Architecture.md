# System Architecture

## Overview

AutoMemory OS consists of a core production AI Memory Service alongside conceptual system interfaces.

---

## Architecture Boundaries

### A. Product Vision & Conceptual Interfaces

The conceptual product vision includes external auxiliary domain services (e.g., Vehicle Service, Recommendation Service, Agent Service). These represent future multi-agent ecosystem integrations.

### B. Current Repository Implementation

The current codebase is concentrated in `services/memory-service/` implementing a production Python/FastAPI memory engine backed by PostgreSQL (`pgvector`), SQLAlchemy, and in-memory Knowledge Graph processing.

---

## Core Memory Service Architecture

```
FastAPI Web App (main.py / routes.py)
  ↓
Memory Pipeline (app/pipeline/memory_pipeline.py)
  ├─ Understanding Engine (app/understanding/)
  ├─ Retrieval Engine (app/retrieval_service.py, app/semantic/)
  ├─ Knowledge Engine (app/knowledge/)
  ├─ Decision Engine (app/decision/)
  ├─ Memory Evolution Engine (app/service.py)
  └─ Knowledge Graph System (app/graph/)
  ↓
Database Layer (PostgreSQL + pgvector + SQLAlchemy)
```

---

## API Endpoints (`routes.py` / `main.py`)

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/` | Service root status |
| `GET` | `/health` | Health check |
| `GET` | `/memory` | Retrieve active memories |
| `POST` | `/memory` | Process & store new memory via pipeline |
| `PUT` | `/memory/{memory_id}` | Update memory |
| `DELETE` | `/memory/{memory_id}` | Delete/archive memory |
| `GET` | `/info` | Service metadata |