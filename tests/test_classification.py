from __future__ import annotations

from vrc.classification import (
    KIND_ASSERTION,
    KIND_ENVIRONMENT,
    KIND_NONE,
    KIND_UNKNOWN,
    classify_failure,
    is_valid_kind,
)


def test_successful_run_is_none() -> None:
    kind, evidence = classify_failure(0, "1 passed", "", timed_out=False)
    assert kind == KIND_NONE
    assert evidence == ""


def test_pytest_assertion_failure_is_evidence() -> None:
    out = "FAILED tests/test_sample.py::test_double - assert 9 == 8\n1 failed in 0.1s"
    kind, evidence = classify_failure(1, out, "E   AssertionError", timed_out=False)
    assert kind == KIND_ASSERTION
    assert "assertionerror" in evidence.lower()


def test_import_error_is_not_evidence_even_with_assertion_text() -> None:
    out = (
        "ERROR collecting tests/test_sample.py\n"
        "ImportError while importing test module '/tmp/base/tests/test_sample.py'.\n"
        "E   ModuleNotFoundError: No module named 'sample'\n"
        "FAILED tests/test_sample.py::test_double\n"
    )
    kind, evidence = classify_failure(2, out, "", timed_out=False)
    assert kind == KIND_ENVIRONMENT
    assert "modulenotfounderror" in evidence.lower()


def test_no_tests_collected_is_environment_error() -> None:
    kind, _ = classify_failure(4, "collected 0 items / 1 error", "", timed_out=False)
    assert kind == KIND_ENVIRONMENT


def test_unrecognised_failure_stays_unknown() -> None:
    kind, evidence = classify_failure(1, "runner exited with a strange status", "", timed_out=False)
    assert kind == KIND_UNKNOWN
    assert evidence == ""


def test_timeout_is_environment_error() -> None:
    kind, _ = classify_failure(124, "FAILED something", "", timed_out=True)
    assert kind == KIND_ENVIRONMENT


def test_custom_markers_are_appended() -> None:
    kind, _ = classify_failure(
        1,
        "vitest: FAIL | expected 2 to be 3",
        "",
        timed_out=False,
        assertion_markers=("fail |",),
    )
    assert kind == KIND_ASSERTION


def test_is_valid_kind() -> None:
    assert all(
        is_valid_kind(k) for k in (KIND_NONE, KIND_ASSERTION, KIND_ENVIRONMENT, KIND_UNKNOWN)
    )
    assert not is_valid_kind("asserted")
