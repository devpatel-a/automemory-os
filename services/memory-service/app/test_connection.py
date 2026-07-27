from database import engine

try:
    with engine.connect():
        print("✅ Connected to PostgreSQL!")
except Exception as e:
    print(e)