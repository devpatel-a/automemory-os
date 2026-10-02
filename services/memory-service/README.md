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
| `0005_memory_version` | `memories.version` (optimistic concurrency, existing rows = 1), `memory_evidence.previous_text` |
| `0006_knowledge_facts` | `knowledge_facts` derived fact index (schema only; populate with `reindex`, below) |

Rollback: `alembic downgrade -1` (each revision has a downgrade; downgrading
0003/0004 drops graph/provenance data).

### Structural fact index (`knowledge_facts`)

The index is derived from `memories.content`. Evolution uses it only to
*discover* candidates in the incoming fact's domain. Each candidate is
re-validated against its memory, and the classifier decides as before. New and
edited memories are indexed automatically. A missing row only loses
structural recall (semantic discovery still applies) until `reindex` repairs it. Existing
databases need an explicit backfill after `alembic upgrade head`; the
migration does not run the NLP model:

```bash
python -m app.knowledge.fact_index reindex        # missing/stale rows; idempotent, resumable
python -m app.knowledge.fact_index reindex --all  # recompute every row
python -m app.knowledge.fact_index check          # read-only audit; exit 1 if inconsistent
```

`reindex` is safe while the service runs: it skips rows locked by live writes
and never modifies memories, evidence, lineage or graph data.

## Configuration

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://localhost/automemory_os` | SQLAlchemy URL |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Must produce 384-dimensional vectors (validated at startup) |
| `SPACY_MODEL` | `en_core_web_sm` | Must be installed |
| `CONTEXT_RETRIEVAL_LIMIT` | `10` | Candidates per context build |
| `CONTEXT_TOKEN_BUDGET` | `1200` | Context budget (characters) |
| `STRUCTURAL_CANDIDATE_LIMIT` | `50` | Live memories examined per fact domain by evolution's structural candidate discovery; `0` disables it |

## API additions (backward compatible)

- `POST /memory`: optional `source_type`, `conversation_id`, `message_id`, `observed_at`.
- `POST /pipeline/process`: optional `source_type`, `conversation_id`, `message_id`;
  the response adds `knowledge_decision` and `reason_codes`.
- `GET /memory/{id}/evidence`: provenance and lineage for one memory.
- `GET /memory` no longer changes `access_count`/`last_accessed` (admin read).
- `POST /agent/query`: `memories_used` is exactly the ContextPackage evidence.
- `PUT /memory/{id}`: an **administrative text correction**, not a knowledge-evolution
  event (it does not supersede or contradict other memories). It locks the fact
  domains and the row, accepts an optional `expected_version` (409 on mismatch),
  recomputes the embedding, rebuilds the memory's graph links, bumps `version`, and
  records an evidence row with the new and previous text. Lifecycle state and
  lineage are unchanged. Responses include `version`.
- `DELETE /memory/{id}`: **archives** by default (reversible; evidence, lineage and
  graph links are kept; an evidence row records the request).
  `DELETE /memory/{id}?purge=true` permanently deletes the memory, its evidence,
  lineage rows and graph links, removes orphaned entities (entities with an
  explicit alias are kept), and records a `lineage_removed_by_purge` evidence row
  on every memory whose lineage pointed at it. **Behavior change:** before v0.10.1,
  a plain DELETE was a hard delete.

## Run

```bash
uvicorn app.main:app
```

Startup validates the spaCy model, the embedding dimension (model vs.
`memories.embedding` column), and database connectivity. It refuses to start
if any check fails.

## Tests

Tests delete data, so they refuse to run unless the database is **both**
named `<name>_test` **and** explicitly approved for destructive tests:

```bash
createdb automemory_os_test
export DATABASE_URL=postgresql://USER@HOST/automemory_os_test
export AUTOMEMORY_TEST_DATABASE=automemory_os_test   # explicit approval (must equal the name)
python -m pytest -q
```

The check runs in the pytest session hooks and inside the destructive helpers
themselves (`app/testing_support.py`).

The test session applies `alembic upgrade head` to the test database first.
