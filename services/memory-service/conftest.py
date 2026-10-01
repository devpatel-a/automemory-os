from app.conftest import ensure_safe_test_database


def pytest_sessionstart(session):
    ensure_safe_test_database()
