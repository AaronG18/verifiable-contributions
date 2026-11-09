"""The verification receipt: a structured record of two independent test runs.

A receipt is deliberately not a signature. It proves nothing by itself. Its
value comes from being produced by CI that the maintainer controls, from the
recorded digests that make post-hoc editing detectable, and from the fact that
a reviewer can re-run the exact command recorded here. See docs/threat-model.md.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1
EXCERPT_LIMIT = 2000

VERDICT_VERIFIED = "VERIFIED"
VERDICT_NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
VERDICT_NEEDS_RERUN = "NEEDS_RERUN"
VERDICT_UNTRUSTED = "UNTRUSTED"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class RunRecord:
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str
    stdout_excerpt: str
    stderr_excerpt: str
    duration_seconds: float
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_excerpt": self.stdout_excerpt,
            "stderr_excerpt": self.stderr_excerpt,
            "duration_seconds": round(self.duration_seconds, 3),
            "timed_out": self.timed_out,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        return cls(
            exit_code=int(data["exit_code"]),
            stdout_sha256=str(data["stdout_sha256"]),
            stderr_sha256=str(data["stderr_sha256"]),
            stdout_excerpt=str(data.get("stdout_excerpt", "")),
            stderr_excerpt=str(data.get("stderr_excerpt", "")),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            timed_out=bool(data.get("timed_out", False)),
        )


@dataclass(frozen=True)
class Receipt:
    repository: str
    base_sha: str
    head_sha: str
    command: tuple[str, ...]
    test_paths: tuple[str, ...]
    test_files_sha256: dict[str, str]
    policy_sha256: str
    environment: dict[str, str]
    base_run: RunRecord
    head_run: RunRecord
    generated_at: str
    verdict: str
    reason: str
    protected_touched: bool = False
    digest: str = field(default="")

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "repository": self.repository,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "command": list(self.command),
            "test_paths": list(self.test_paths),
            "test_files_sha256": dict(sorted(self.test_files_sha256.items())),
            "policy_sha256": self.policy_sha256,
            "environment": dict(sorted(self.environment.items())),
            "base_run": self.base_run.to_dict(),
            "head_run": self.head_run.to_dict(),
            "generated_at": self.generated_at,
            "verdict": self.verdict,
            "reason": self.reason,
            "protected_touched": self.protected_touched,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload()
        payload["digest"] = self.digest or sha256_text(canonical(payload))
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Receipt:
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(f"unsupported receipt schema_version: {data.get('schema_version')!r}")
        return cls(
            repository=str(data["repository"]),
            base_sha=str(data["base_sha"]),
            head_sha=str(data["head_sha"]),
            command=tuple(data["command"]),
            test_paths=tuple(data["test_paths"]),
            test_files_sha256=dict(data["test_files_sha256"]),
            policy_sha256=str(data["policy_sha256"]),
            environment=dict(data["environment"]),
            base_run=RunRecord.from_dict(data["base_run"]),
            head_run=RunRecord.from_dict(data["head_run"]),
            generated_at=str(data["generated_at"]),
            verdict=str(data["verdict"]),
            reason=str(data["reason"]),
            protected_touched=bool(data.get("protected_touched", False)),
            digest=str(data.get("digest", "")),
        )


def derive_verdict(base: RunRecord, head: RunRecord, protected_touched: bool) -> tuple[str, str]:
    """Recompute the verdict from raw observations.

    Kept as a pure function so `vrc check` can detect a receipt whose verdict
    was edited after the fact.
    """
    if protected_touched:
        return (
            VERDICT_UNTRUSTED,
            "The change modifies the verifier or its policy. A human must review "
            "the verifier change before its output can be trusted.",
        )
    if base.timed_out or head.timed_out:
        return (
            VERDICT_NEEDS_RERUN,
            "A test run timed out; the environment did not complete the check.",
        )
    if head.exit_code != 0:
        return (
            VERDICT_NEEDS_RERUN,
            "The tests do not pass on the proposed head. This is a failing build "
            "or an environment mismatch, not evidence for the change.",
        )
    if base.exit_code == 0:
        return (
            VERDICT_NEEDS_EVIDENCE,
            "The new tests pass without the proposed change, so they do not "
            "demonstrate the claimed behaviour. Add a test that fails on the base ref.",
        )
    return (
        VERDICT_VERIFIED,
        "The attached tests fail on the base ref and pass on the proposed head "
        "in this environment.",
    )


def check_receipt(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the internal consistency of a receipt. Returns (ok, problems)."""
    problems: list[str] = []
    try:
        receipt = Receipt.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        return False, [f"malformed receipt: {exc}"]

    expected_digest = sha256_text(canonical(receipt.payload()))
    if not receipt.digest:
        problems.append("missing digest")
    elif receipt.digest != expected_digest:
        problems.append("digest mismatch: the receipt was edited after it was produced")

    expected_verdict, expected_reason = derive_verdict(
        receipt.base_run, receipt.head_run, receipt.protected_touched
    )
    if receipt.verdict != expected_verdict:
        problems.append(
            f"verdict {receipt.verdict!r} does not match the recorded runs (expected {expected_verdict!r})"
        )
    if receipt.reason != expected_reason:
        problems.append("reason does not match the recorded runs")

    for label, run in (("base", receipt.base_run), ("head", receipt.head_run)):
        for stream in ("stdout", "stderr"):
            value = getattr(run, f"{stream}_sha256")
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                problems.append(f"{label}.{stream}_sha256 is not a sha256 hex digest")

    for name, digest in receipt.test_files_sha256.items():
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            problems.append(f"test file digest for {name!r} is not a sha256 hex digest")
    if len(receipt.policy_sha256) != 64:
        problems.append("policy_sha256 is not a sha256 hex digest")
    if not receipt.command:
        problems.append("command is empty")
    for field_name in ("base_sha", "head_sha"):
        value = getattr(receipt, field_name)
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            problems.append(f"{field_name} is not a full commit sha")

    return not problems, problems
