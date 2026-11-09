"""Command line interface for vrc."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import __version__
from .config import ConfigError
from .receipt import Receipt, check_receipt
from .replay import ReplayError, replay
from .report import render_markdown

VERDICTS = ("VERIFIED", "NEEDS_EVIDENCE", "NEEDS_RERUN", "UNTRUSTED")


def _load_receipt(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read receipt {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("receipt must be a JSON object")
    return data


def _cmd_replay(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    with tempfile.TemporaryDirectory(prefix="vrc-") as tmp:
        outcome = replay(
            repo,
            args.base,
            args.head,
            workdir=Path(tmp),
            repository=args.repository,
        )
        receipt = outcome.receipt
        text = receipt.to_json()
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        if args.format == "markdown":
            sys.stdout.write(render_markdown(receipt))
        elif args.format == "summary":
            print(
                json.dumps(
                    {
                        "verdict": receipt.verdict,
                        "reason": receipt.reason,
                        "base_exit_code": receipt.base_run.exit_code,
                        "head_exit_code": receipt.head_run.exit_code,
                        "test_files": len(receipt.test_files_sha256),
                    },
                    indent=2,
                )
            )
        else:
            sys.stdout.write(text)
    print(f"vrc: {receipt.verdict} - {receipt.reason}", file=sys.stderr)
    for verdict in args.fail_on.split(","):
        if verdict.strip() and verdict.strip() == receipt.verdict:
            return 1
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        data = _load_receipt(Path(args.receipt))
    except ValueError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 2
    ok, problems = check_receipt(data)
    if ok:
        print(f"OK: receipt is internally consistent (verdict={data.get('verdict')})")
        return 0
    for problem in problems:
        print(f"INVALID: {problem}", file=sys.stderr)
    return 1


def _cmd_explain(args: argparse.Namespace) -> int:
    try:
        receipt = Receipt.from_dict(_load_receipt(Path(args.receipt)))
    except (ValueError, KeyError, TypeError) as exc:
        print(f"cannot render receipt: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render_markdown(receipt))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vrc",
        description="Independently replay the tests attached to a change proposal.",
    )
    parser.add_argument("--version", action="version", version=f"vrc {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_replay = sub.add_parser("replay", help="replay tests on base and head trees")
    p_replay.add_argument("--repo", default=".", help="path to the git repository")
    p_replay.add_argument("--base", required=True, help="base ref (before the change)")
    p_replay.add_argument("--head", required=True, help="head ref (with the change)")
    p_replay.add_argument(
        "--repository", default=None, help="repository identifier for the receipt"
    )
    p_replay.add_argument("--output", default=None, help="write the receipt JSON here")
    p_replay.add_argument("--format", choices=("json", "summary", "markdown"), default="json")
    p_replay.add_argument(
        "--fail-on",
        default="",
        help="comma-separated verdicts that should produce a non-zero exit code, "
        "e.g. NEEDS_EVIDENCE,NEEDS_RERUN. Empty means report-only.",
    )
    p_replay.set_defaults(func=_cmd_replay)

    p_check = sub.add_parser("check", help="validate a receipt's internal consistency")
    p_check.add_argument("receipt")
    p_check.set_defaults(func=_cmd_check)

    p_explain = sub.add_parser("explain", help="render a receipt as Markdown")
    p_explain.add_argument("receipt")
    p_explain.set_defaults(func=_cmd_explain)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ReplayError, ConfigError) as exc:
        print(f"vrc: error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
