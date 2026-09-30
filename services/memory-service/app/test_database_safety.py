import subprocess
import sys
import os

import pytest

from app.testing_support import UnsafeTestDatabaseError, assert_test_database


@pytest.mark.parametrize("url", [
    "postgresql://localhost/automemory_os",
    "postgresql://devpatel@localhost/automemory_os",
    "postgresql://user:secret@prod-db:5432/memories",
    "postgresql://localhost/",
])
def test_guard_refuses_non_test_databases(url):
    with pytest.raises(UnsafeTestDatabaseError, match="Refusing destructive"):
        assert_test_database(url)


@pytest.mark.parametrize("url", [
    "postgresql://localhost/automemory_os_test",
    "postgresql://ci@db/test_automemory",
])
def test_guard_allows_test_databases(url):
    assert "test" in assert_test_database(url)


def test_current_session_uses_a_test_database():
    assert "test" in assert_test_database()


def test_pytest_session_refuses_to_start_on_non_test_database():
    """End-to-end: pytest exits before any test runs when DATABASE_URL is not a test DB."""
    env = dict(os.environ, DATABASE_URL="postgresql://localhost/automemory_os")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "app/test_config.py"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 4, result.stdout + result.stderr
    assert "Refusing destructive test operation" in result.stdout + result.stderr
