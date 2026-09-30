"""
Destructive tests may only run against an explicitly named AND explicitly
approved test database. A name merely containing "test" is not enough.
"""

import os
import subprocess
import sys

import pytest

from app.testing_support import (
    APPROVAL_ENV,
    UnsafeTestDatabaseError,
    assert_scratch_test_database_name,
    assert_test_database,
    reset_database,
)


@pytest.mark.parametrize("url", [
    "postgresql://localhost/automemory_os",                    # normal development DB
    "postgresql://devpatel@localhost/automemory_os",
    "postgresql://user:secret@prod-db:5432/memories",          # production-like
    "postgresql://user:secret@prod-db:5432/automemory_prod",
    "postgresql://localhost/contest_prod",                     # contains "test"
    "postgresql://localhost/latest_backup",                    # contains "test"
    "postgresql://ci@db/test_automemory",                      # "test" prefix only
    "postgresql://localhost/automemory_os_test_copy",          # not a *_test name
    "postgresql://localhost/Automemory_OS_TEST",               # wrong case
    "postgresql://localhost/",
])
def test_guard_rejects_unsafe_database_names_even_when_approved(url):
    name = url.rsplit("/", 1)[-1]
    with pytest.raises(UnsafeTestDatabaseError, match="Refusing destructive"):
        assert_test_database(url, approved=name)


def test_guard_rejects_correctly_named_but_unapproved_database():
    with pytest.raises(UnsafeTestDatabaseError, match="not approved"):
        assert_test_database("postgresql://localhost/automemory_os_test", approved="")
    with pytest.raises(UnsafeTestDatabaseError, match="not approved"):
        assert_test_database("postgresql://localhost/automemory_os_test", approved="other_test")


def test_guard_accepts_explicitly_approved_test_database():
    assert assert_test_database(
        "postgresql://localhost/automemory_os_test", approved="automemory_os_test",
    ) == "automemory_os_test"


def test_current_session_uses_an_approved_test_database():
    assert assert_test_database() == os.environ[APPROVAL_ENV]


def test_destructive_helper_checks_the_guard_itself(monkeypatch):
    """reset_database() refuses on its own, independent of the pytest hooks."""
    monkeypatch.setenv(APPROVAL_ENV, "some_other_test")
    with pytest.raises(UnsafeTestDatabaseError, match="not approved"):
        reset_database()


def test_scratch_database_names_must_be_test_names():
    assert assert_scratch_test_database_name("automemory_migration_ab12_test")
    with pytest.raises(UnsafeTestDatabaseError):
        assert_scratch_test_database_name("automemory_os")


def _pytest_with(database_url, approved):
    env = dict(os.environ, DATABASE_URL=database_url)
    env.pop(APPROVAL_ENV, None)
    if approved is not None:
        env[APPROVAL_ENV] = approved
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "app/test_config.py"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=300,
    )


@pytest.mark.parametrize("database_url, approved", [
    ("postgresql://localhost/automemory_os", "automemory_os"),          # normal DB, even if "approved"
    ("postgresql://localhost/contest_prod", "contest_prod"),            # contains "test"
    ("postgresql://localhost/automemory_os_test", None),                # right name, no approval
])
def test_pytest_session_refuses_to_start(database_url, approved):
    """End-to-end: pytest exits (code 4) before any test runs."""
    result = _pytest_with(database_url, approved)
    assert result.returncode == 4, result.stdout + result.stderr
    assert "Refusing destructive test operation" in result.stdout + result.stderr
