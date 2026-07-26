# System Architecture

## Overview

AutoMemory OS is divided into independent services.

Each service has one responsibility and communicates with other services through APIs.

---

## Services

### Memory Service

Responsible for:

- Storing memories
- Retrieving memories
- Updating memories
- Forgetting memories

---

### Context Service

Responsible for:

- Current location
- Weather
- Time
- Battery
- Vehicle context

---

### Vehicle Service

Responsible for:

- Vehicle state
- Speed
- Temperature
- Battery level
- Sensors

---

### Recommendation Service

Responsible for:

- Route suggestions
- Charging suggestions
- Restaurant suggestions

---

### Agent Service

Responsible for:

- AI reasoning
- Task planning
- Tool execution

---

## Memory Service Endpoints

- GET /
- GET /health
- GET /memory
- GET /info

---

## Memory Model

```text
Memory

↓

memory : string