from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from vrc.receipt import (
    Receipt,
    RunRecord,
    canonical,
    check_receipt,
    derive_verdict,
    sha256_text,
)


@pytest.fixture
def receipt_data() -> dict:
    base = RunRecord(1, "a" * 64, "b" * 64, "assert failed", "", 0.4)
    head = RunRecord(0, "c" * 64, "d" * 64, "1 passed", "", 0.5)
    verdict, reason = derive_verdict(base, head, False)
    receipt = Receipt(
        repository="owner/repo",
        base_sha="1" * 40,
        head_sha="2" * 40,
        command=("python", "-m", "pytest", "-q"),
        test_paths=("tests",),
        test_files_sha256={"tests/test_sample.py": "e" * 64},
        policy_sha256="f" * 64,
        environment={"python": "3.12"},
        base_run=base,
        head_run=head,
        generated_at="2026-11-10T00:00:00+00:00",
        verdict=verdict,
        reason=reason,
    )
    return receipt.to_dict()


def test_valid_receipt_passes(receipt_data: dict) -> None:
    ok, problems = check_receipt(receipt_data)
    assert ok, problems


def test_tampered_verdict_is_detected(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["verdict"] = "VERIFIED" if data["verdict"] != "VERIFIED" else "NEEDS_EVIDENCE"
    ok, problems = check_receipt(data)
    assert not ok
    assert any("verdict" in p for p in problems)


def test_tampered_exit_code_is_detected_by_digest(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["base_run"]["exit_code"] = 0
    ok, problems = check_receipt(data)
    assert not ok
    assert any("digest" in p for p in problems)


def test_recomputing_digest_does_not_hide_an_inconsistent_verdict(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["base_run"]["exit_code"] = 0
    payload = {k: v for k, v in data.items() if k != "digest"}
    data["digest"] = sha256_text(canonical(payload))
    ok, problems = check_receipt(data)
    assert not ok
    assert any("does not match" in p for p in problems)


def test_missing_digest_is_detected(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data.pop("digest")
    ok, problems = check_receipt(data)
    assert not ok
    assert any("missing digest" in p for p in problems)


def test_unsupported_schema_is_rejected(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["schema_version"] = 999
    ok, problems = check_receipt(data)
    assert not ok


def test_malformed_sha_is_detected(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["base_sha"] = "abc"
    # digest would also mismatch; check that the sha complaint is present
    ok, problems = check_receipt(data)
    assert not ok
    assert any("base_sha" in p for p in problems)


def test_bad_hash_is_detected(receipt_data: dict) -> None:
    data = copy.deepcopy(receipt_data)
    data["base_run"]["stdout_sha256"] = "not-a-hash"
    ok, problems = check_receipt(data)
    assert not ok
    assert any("stdout_sha256" in p for p in problems)


def test_roundtrip_json(tmp_path: Path, receipt_data: dict) -> None:
    receipt = Receipt.from_dict(receipt_data)
    path = tmp_path / "receipt.json"
    path.write_text(receipt.to_json(), encoding="utf-8")
    assert json.loads(path.read_text(encoding="utf-8")) == receipt_data


def test_verdict_derivation_covers_all_outcomes() -> None:
    fail = RunRecord(1, "a" * 64, "b" * 64, "", "", 0.1)
    ok = RunRecord(0, "c" * 64, "d" * 64, "", "", 0.1)
    timeout = RunRecord(124, "c" * 64, "d" * 64, "", "", 0.1, timed_out=True)
    assert derive_verdict(fail, ok, False)[0] == "VERIFIED"
    assert derive_verdict(ok, ok, False)[0] == "NEEDS_EVIDENCE"
    assert derive_verdict(fail, fail, False)[0] == "NEEDS_RERUN"
    assert derive_verdict(timeout, ok, False)[0] == "NEEDS_RERUN"
    assert derive_verdict(fail, ok, True)[0] == "UNTRUSTED"
