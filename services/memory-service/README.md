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
tables and leaves them untouched. Do not use `automemory_os_backup.sql` as a
schema source.

## Configuration

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://localhost/automemory_os` | SQLAlchemy URL |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Must produce 384-dimensional vectors (validated at startup) |
| `SPACY_MODEL` | `en_core_web_sm` | Must be installed |
| `CONTEXT_RETRIEVAL_LIMIT` | `10` | Candidates per context build |
| `CONTEXT_TOKEN_BUDGET` | `1200` | Context budget (characters) |

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
