# AutoMemory OS — Memory Service

## Install

```bash
cd services/memory-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # runtime (includes the pinned spaCy model)
pip install -r requirements-dev.txt    # + test tooling
```

The spaCy model `en_core_web_sm` is a pinned install-time dependency. The
service never downloads models at runtime: if the model is missing, startup
fails with an actionable error.

## Database

PostgreSQL with the `vector` extension (pgvector) is required.

```bash
export DATABASE_URL=postgresql://USER@HOST/automemory_os
alembic upgrade head                   # creates or upgrades the schema
```

`alembic upgrade head` also works on databases created by the older
`Base.metadata.create_all()` path: the baseline revision detects existing
tables and leaves them untouched, and later revisions only add constraints,
indexes and tables. Constraints that legacy rows would violate are added
`NOT VALID` (enforced for new writes) and reported, never "fixed" by deleting
data. `python -m app.init_db` is equivalent to `alembic upgrade head`.

| Revision | Adds |
| :--- | :--- |
| `0001_baseline` | `memories`, `memory_relationships` (the v0.9 schema) |
| `0002_integrity_constraints` | FKs with cascade rules, unique lineage rows, no self-links, lifecycle-state CHECK, indexes, full-text GIN index |
| `0003_knowledge_graph` | `entities`, `entity_aliases`, `memory_entities`, `entity_relationships` |
| `0004_memory_evidence` | provenance (`memory_evidence`), legacy rows backfilled as `source_type='legacy'` |

Rollback: `alembic downgrade -1` (each revision has a downgrade; downgrading
0003/0004 drops graph/provenance data).

## Configuration

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://localhost/automemory_os` | SQLAlchemy URL |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Must produce 384-dimensional vectors (validated at startup) |
| `SPACY_MODEL` | `en_core_web_sm` | Must be installed |
| `CONTEXT_RETRIEVAL_LIMIT` | `10` | Candidates per context build |
| `CONTEXT_TOKEN_BUDGET` | `1200` | Context budget (characters) |

## API additions (backward compatible)

- `POST /memory`: optional `source_type`, `conversation_id`, `message_id`, `observed_at`.
- `POST /pipeline/process`: optional `source_type`, `conversation_id`, `message_id`;
  the response adds `knowledge_decision` and `reason_codes`.
- `GET /memory/{id}/evidence`: provenance and lineage for one memory.
- `GET /memory` no longer changes `access_count`/`last_accessed` (admin read).
- `POST /agent/query`: `memories_used` is exactly the ContextPackage evidence.

## Run

```bash
uvicorn app.main:app
```

Startup validates the spaCy model, the embedding dimension (model vs.
`memories.embedding` column), and database connectivity. It refuses to start
if any check fails.

## Tests

Tests delete data, so they refuse to run unless `DATABASE_URL` names a
database whose name contains `test`:

```bash
createdb automemory_os_test
export DATABASE_URL=postgresql://USER@HOST/automemory_os_test
python -m pytest -q
```

The test session applies `alembic upgrade head` to the test database first.
