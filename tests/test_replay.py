from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.helpers import BUGGY_MODULE, CATCHING_TEST, FIXED_MODULE, VACUOUS_TEST, git
from vrc.receipt import (
    VERDICT_NEEDS_EVIDENCE,
    VERDICT_NEEDS_RERUN,
    VERDICT_UNTRUSTED,
    VERDICT_VERIFIED,
)
from vrc.replay import ReplayError, replay


def _policy(command: list[str]) -> str:
    return f'command = {json.dumps(command)}\ntest_paths = ["tests/"]\ntimeout_seconds = 120\n'


@pytest.fixture
def command(python_command: list[str]) -> list[str]:
    return python_command


def test_verified_when_test_fails_on_base_and_passes_on_head(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")

    outcome = replay(repo, base, head, workdir=tmp_path / "work", repository="test/repo")
    r = outcome.receipt
    assert r.verdict == VERDICT_VERIFIED
    assert r.base_run.exit_code != 0
    assert r.head_run.exit_code == 0
    assert r.base_sha == base and r.head_sha == head
    assert "tests/test_sample.py" in r.test_files_sha256
    assert r.protected_touched is False
    assert r.to_dict()["digest"]


def test_needs_evidence_when_test_is_vacuous(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, VACUOUS_TEST, message="fix without a real test")

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.verdict == VERDICT_NEEDS_EVIDENCE
    assert outcome.receipt.base_run.exit_code == 0
    assert "do not" in outcome.receipt.reason


def test_needs_rerun_when_head_tests_fail(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    broken = "def test_broken():\n    assert False, 'intentional'\n"
    head = commit(FIXED_MODULE, broken, message="broken test")

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.verdict == VERDICT_NEEDS_RERUN
    assert outcome.receipt.head_run.exit_code != 0


def test_untrusted_when_verifier_itself_is_modified(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")
    (repo / "vrc").mkdir(exist_ok=True)
    (repo / "vrc" / "__init__.py").write_text("# tampered\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "tamper with verifier")
    head = git(repo, "rev-parse", "HEAD").strip()

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.verdict == VERDICT_UNTRUSTED
    assert outcome.receipt.protected_touched is True


def test_untrusted_when_dependabot_config_is_modified(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    commit(FIXED_MODULE, CATCHING_TEST, message="fix")
    (repo / ".github").mkdir(exist_ok=True)
    (repo / ".github" / "dependabot.yml").write_text("version: 2\nupdates: []\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "weaken dependabot config")
    head = git(repo, "rev-parse", "HEAD").strip()

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.verdict == VERDICT_UNTRUSTED
    assert outcome.receipt.protected_touched is True


def test_policy_is_read_from_base_not_head(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")
    (repo / ".vrc.toml").write_text('command = ["rm", "-rf", "/"]\n', encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "malicious policy on head")
    head = git(repo, "rev-parse", "HEAD").strip()

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.command[0] == command[0]
    assert outcome.receipt.verdict == VERDICT_UNTRUSTED


def test_source_change_is_not_copied_to_base_tree(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")

    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    base_module = (outcome.base_dir / "sample.py").read_text(encoding="utf-8")
    base_test = (outcome.base_dir / "tests" / "test_sample.py").read_text(encoding="utf-8")
    assert base_module == BUGGY_MODULE
    assert base_test == CATCHING_TEST


def test_no_test_files_is_an_error(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, None, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, None, message="fix with no tests")
    with pytest.raises(ReplayError, match="no test files"):
        replay(repo, base, head, workdir=tmp_path / "work")


def test_same_commit_is_rejected(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    sha = commit(BUGGY_MODULE, VACUOUS_TEST, message="only", policy=_policy(command))
    with pytest.raises(ReplayError, match="same commit"):
        replay(repo, sha, sha, workdir=tmp_path / "work")


def test_receipt_command_is_reproducible(tmp_path, scenario, command) -> None:
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")
    outcome = replay(repo, base, head, workdir=tmp_path / "work")
    assert outcome.receipt.command == tuple(command)
    assert outcome.receipt.environment["python"] == sys.version.split()[0]
    assert Path(outcome.head_dir, "sample.py").read_text(encoding="utf-8") == FIXED_MODULE
