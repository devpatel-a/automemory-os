# SQL Fundamentals

## SQL

SQL (Structured Query Language) is used to communicate with relational databases.

---

## CRUD Mapping

| CRUD | HTTP | SQL |
|------|------|-----|
| Create | POST | INSERT |
| Read | GET | SELECT |
| Update | PUT | UPDATE |
| Delete | DELETE | DELETE |

---

## Memory Table

| Column | Type |
|---------|------|
| id | Integer |
| memory | Text |
| created_at | Timestamp |

---

## PostgreSQL Setup

### Database

automemory_os

### Table

memories

| Column | Type |
|---------|------|
| id | SERIAL PRIMARY KEY |
| memory | TEXT |
| created_at | TIMESTAMP |