"""
Session-wide test safety.

The suite deletes rows, so it refuses to run unless DATABASE_URL names an
explicitly named (<name>_test) AND explicitly approved
(AUTOMEMORY_TEST_DATABASE=<name>) test database (see app/testing_support.py).
Enforced here and inside the destructive helpers themselves:
- services/memory-service/conftest.py: pytest_sessionstart (before collection
  when pytest runs from services/memory-service);
- the autouse session fixture below, which applies whenever any test in app/
  runs, whatever directory pytest was started from.
"""

import pytest

from app.testing_support import UnsafeTestDatabaseError, assert_test_database, prepare_test_schema


def ensure_safe_test_database():
    try:
        assert_test_database()
    except UnsafeTestDatabaseError as exc:
        pytest.exit(str(exc), returncode=4)


@pytest.fixture(scope="session", autouse=True)
def _safe_test_database():
    ensure_safe_test_database()
    prepare_test_schema()
    yield
