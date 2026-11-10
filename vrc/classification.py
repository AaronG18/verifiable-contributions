"""Classify *why* a test command failed.

A non-zero exit code is not evidence on its own. A missing dependency, a
collection error and a genuine assertion failure all produce exit code 1, but
only the last one demonstrates that a test detected the change under review.

Markers are deliberately conservative and cover common runners. Repositories
can append their own via the policy file; anything unrecognised is UNKNOWN and
is never treated as evidence.
"""

from __future__ import annotations

# Signals that the tests did not actually run. Checked first: if the suite
# could not even be collected, no assertion anywhere in the output counts.
DEFAULT_ENVIRONMENT_MARKERS: tuple[str, ...] = (
    "modulenotfounderror",
    "importerror",
    "cannot import name",
    "no module named",
    "error collecting",
    "error: collecting",
    "import error",
    "no tests ran",
    "no tests collected",
    "collected 0 items",
    "found no collectors",
    "file or directory not found",
    "no such file or directory",
    "command not found",
    "not recognized as an internal or external command",
    "syntaxerror",
    "indentationerror",
    "internalerror",
    "cannot find module",
    "err_module_not_found",
    "could not start command",
)

# Signals that a test executed and its assertion failed.
DEFAULT_ASSERTION_MARKERS: tuple[str, ...] = (
    "assertionerror",
    "assert ",
    "failed ",
    " fail:",
    "--- fail:",
    "= failures =",
    "short test summary info",
    "1 failed",
    "failed (failures",
    "expect(",
    "comparisondifference",
    "not equal to expected",
    "test failure",
)

KIND_NONE = "none"
KIND_ASSERTION = "assertion"
KIND_ENVIRONMENT = "environment"
KIND_UNKNOWN = "unknown"

_KINDS = (KIND_NONE, KIND_ASSERTION, KIND_ENVIRONMENT, KIND_UNKNOWN)


def is_valid_kind(value: str) -> bool:
    return value in _KINDS


def classify_failure(
    exit_code: int,
    stdout: str,
    stderr: str,
    *,
    timed_out: bool,
    environment_markers: tuple[str, ...] = DEFAULT_ENVIRONMENT_MARKERS,
    assertion_markers: tuple[str, ...] = DEFAULT_ASSERTION_MARKERS,
) -> tuple[str, str]:
    """Return (kind, evidence). Evidence is one matching line, for a reviewer."""
    if exit_code == 0:
        return KIND_NONE, ""
    if timed_out:
        return KIND_ENVIRONMENT, "the command exceeded its timeout and was terminated"

    blob = f"{stdout}\n{stderr}".lower()
    lines = [line.strip() for line in blob.splitlines() if line.strip()]

    # The evidence is the matching line verbatim, not a description of it.
    # `check_receipt` re-runs classify_failure() on this string so a receipt
    # whose failure_kind was edited can be detected.
    for marker in environment_markers:
        for line in lines:
            if marker in line:
                return KIND_ENVIRONMENT, line[:300]

    for marker in assertion_markers:
        for line in lines:
            if marker in line:
                return KIND_ASSERTION, line[:300]

    return KIND_UNKNOWN, ""
