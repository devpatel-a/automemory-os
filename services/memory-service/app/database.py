from sqlalchemy import create_engine

DATABASE_URL = "postgresql://devpatel@localhost/automemory_os"

engine = create_engine(DATABASE_URL)

connection = engine.connect()

print("✅ Connected to PostgreSQL!")