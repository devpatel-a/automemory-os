from app.database import engine


def test_postgres_connection():
    with engine.connect():
        pass