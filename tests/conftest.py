"""Hermetic fixtures: build real git repositories with real commits."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.helpers import git


@pytest.fixture
def scenario(tmp_path: Path):
    """Return a helper that commits a snapshot and yields the repo path."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "vrc@example.invalid")
    git(repo, "config", "user.name", "vrc test")
    os.environ.update(
        {
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
        }
    )

    def commit(module: str, test: str | None, *, message: str, policy: str | None = None) -> str:
        (repo / "sample.py").write_text(module, encoding="utf-8")
        tests = repo / "tests"
        tests.mkdir(exist_ok=True)
        test_file = tests / "test_sample.py"
        if test is None:
            test_file.unlink(missing_ok=True)
        else:
            test_file.write_text(test, encoding="utf-8")
        if policy is not None:
            (repo / ".vrc.toml").write_text(policy, encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", message)
        return git(repo, "rev-parse", "HEAD").strip()

    return repo, commit


@pytest.fixture
def python_command() -> list[str]:
    """A command that works in the extracted tree without installing anything."""
    return [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
