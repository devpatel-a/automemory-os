# Database Fundamentals

## Why We Need a Database

The Memory Service currently stores data in a Python list.

This data is temporary and is lost whenever the server restarts.

A database provides permanent storage.

---

## Why PostgreSQL?

- Open source
- Reliable
- Production ready
- Excellent FastAPI support

---

## Memory Table (Initial Design)

| Column | Type | Purpose |
|---------|------|---------|
| id | Integer | Unique identifier |
| memory | Text | Memory content |
| created_at | Timestamp | Creation time |

---

## SQLAlchemy Connection

Connection URL:

postgresql://devpatel@localhost/automemory_os

Components:

- PostgreSQL
- SQLAlchemy Engine
- PostgreSQL Driver (psycopg2)