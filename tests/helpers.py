"""Shared constants and git helpers for the hermetic replay scenarios."""

from __future__ import annotations

import subprocess
from pathlib import Path

BUGGY_MODULE = "def double(value: int) -> int:\n    return value + value + 1\n"
FIXED_MODULE = "def double(value: int) -> int:\n    return value + value\n"

CATCHING_TEST = """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sample import double


def test_double_is_twice():
    assert double(4) == 8
"""

VACUOUS_TEST = """\
def test_something_runs():
    assert 1 == 1
"""


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=True,
    )
    return proc.stdout.decode()
