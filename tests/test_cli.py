from __future__ import annotations

import json

import pytest

from tests.helpers import BUGGY_MODULE, CATCHING_TEST, FIXED_MODULE, VACUOUS_TEST
from vrc.cli import main


def _policy(command: list[str]) -> str:
    return f'command = {json.dumps(command)}\ntest_paths = ["tests/"]\ntimeout_seconds = 120\n'


@pytest.fixture
def ready_repo(scenario, python_command):
    repo, commit = scenario
    base = commit(BUGGY_MODULE, VACUOUS_TEST, message="base", policy=_policy(python_command))
    head = commit(FIXED_MODULE, CATCHING_TEST, message="fix")
    return repo, base, head


def test_replay_writes_receipt_and_prints_summary(tmp_path, ready_repo, capsys) -> None:
    repo, base, head = ready_repo
    output = tmp_path / "out" / "receipt.json"
    code = main(
        [
            "replay",
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--output",
            str(output),
            "--format",
            "summary",
            "--repository",
            "owner/repo",
        ]
    )
    assert code == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["verdict"] == "VERIFIED"
    assert data["repository"] == "owner/repo"
    captured = capsys.readouterr()
    assert "VERIFIED" in captured.out
    assert "VERIFIED" in captured.err


def test_fail_on_returns_nonzero(tmp_path, ready_repo) -> None:
    repo, base, head = ready_repo
    code = main(
        [
            "replay",
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--output",
            str(tmp_path / "r.json"),
            "--format",
            "summary",
            "--fail-on",
            "NEEDS_EVIDENCE,NEEDS_RERUN",
        ]
    )
    assert code == 0
    code = main(
        [
            "replay",
            "--repo",
            str(repo),
            "--base",
            base,
            "--head",
            head,
            "--output",
            str(tmp_path / "r2.json"),
            "--format",
            "summary",
            "--fail-on",
            "VERIFIED",
        ]
    )
    assert code == 1


def test_check_accepts_generated_receipt(tmp_path, ready_repo, capsys) -> None:
    repo, base, head = ready_repo
    path = tmp_path / "r.json"
    assert (
        main(
            [
                "replay",
                "--repo",
                str(repo),
                "--base",
                base,
                "--head",
                head,
                "--output",
                str(path),
                "--format",
                "summary",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["check", str(path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_check_rejects_tampered_receipt(tmp_path, ready_repo, capsys) -> None:
    repo, base, head = ready_repo
    path = tmp_path / "r.json"
    assert (
        main(
            [
                "replay",
                "--repo",
                str(repo),
                "--base",
                base,
                "--head",
                head,
                "--output",
                str(path),
                "--format",
                "summary",
            ]
        )
        == 0
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["head_run"]["exit_code"] = 1
    path.write_text(json.dumps(data), encoding="utf-8")
    capsys.readouterr()
    assert main(["check", str(path)]) == 1
    assert "INVALID" in capsys.readouterr().err


def test_check_rejects_missing_file(tmp_path) -> None:
    assert main(["check", str(tmp_path / "nope.json")]) == 2


def test_explain_renders_markdown(tmp_path, ready_repo, capsys) -> None:
    repo, base, head = ready_repo
    path = tmp_path / "r.json"
    assert (
        main(
            [
                "replay",
                "--repo",
                str(repo),
                "--base",
                base,
                "--head",
                head,
                "--output",
                str(path),
                "--format",
                "summary",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["explain", str(path)]) == 0
    out = capsys.readouterr().out
    assert "## Verification receipt" in out
    assert "Base" in out and "Head" in out


def test_replay_reports_error_for_same_commit(scenario, python_command, tmp_path) -> None:
    repo, commit = scenario
    sha = commit(BUGGY_MODULE, VACUOUS_TEST, message="only", policy=_policy(python_command))
    code = main(
        [
            "replay",
            "--repo",
            str(repo),
            "--base",
            sha,
            "--head",
            sha,
            "--output",
            str(tmp_path / "r.json"),
            "--format",
            "summary",
        ]
    )
    assert code == 2


def test_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "vrc" in capsys.readouterr().out
