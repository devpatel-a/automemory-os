"""
Create or upgrade the database schema.

Schema is managed by Alembic migrations (services/memory-service/alembic);
this is a convenience wrapper equivalent to 'alembic upgrade head'.
Base.metadata.create_all() is no longer used for schema management.
"""

from app.testing_support import run_migrations

if __name__ == "__main__":
    run_migrations()
    print("Database schema is at the latest migration.")
