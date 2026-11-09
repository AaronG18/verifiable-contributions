"""Load the verification policy from the base ref only."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .classification import DEFAULT_ASSERTION_MARKERS, DEFAULT_ENVIRONMENT_MARKERS

CONFIG_NAME = ".vrc.toml"

DEFAULT_COMMAND: tuple[str, ...] = ("python", "-m", "pytest", "-q")
DEFAULT_TEST_PATHS: tuple[str, ...] = ("tests", "test")
DEFAULT_PROTECTED_PATHS: tuple[str, ...] = (
    "vrc/",
    "action.yml",
    ".vrc.toml",
    ".github/workflows/receipt.yml",
    ".github/dependabot.yml",
    "SECURITY.md",
    "pyproject.toml",
)


class ConfigError(ValueError):
    """Raised when the verification policy is missing or malformed."""


@dataclass(frozen=True)
class Config:
    command: tuple[str, ...]
    test_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    timeout_seconds: int
    environment_markers: tuple[str, ...]
    assertion_markers: tuple[str, ...]

    @classmethod
    def default(cls) -> Config:
        return cls(
            command=DEFAULT_COMMAND,
            test_paths=DEFAULT_TEST_PATHS,
            protected_paths=DEFAULT_PROTECTED_PATHS,
            timeout_seconds=300,
            environment_markers=DEFAULT_ENVIRONMENT_MARKERS,
            assertion_markers=DEFAULT_ASSERTION_MARKERS,
        )

    @classmethod
    def load(cls, source: Path | bytes) -> Config:
        if isinstance(source, bytes):
            raw = source
        else:
            if not source.is_file():
                raise ConfigError(f"policy file not found: {source}")
            raw = source.read_bytes()
        try:
            data = tomllib.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"invalid {CONFIG_NAME}: {exc}") from exc

        command = data.get("command", list(DEFAULT_COMMAND))
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) and part for part in command)
        ):
            raise ConfigError("command must be a non-empty list of non-empty strings")
        executable = Path(command[0]).name.lower()
        for suffix in (".exe", ".cmd", ".bat"):
            if executable.endswith(suffix):
                executable = executable[: -len(suffix)]
        allowlisted = {"python", "python3", "pytest", "uv", "tox", "npm", "pnpm", "go"}
        if executable not in allowlisted and not executable.startswith("python3."):
            raise ConfigError(f"command executable {command[0]!r} is not allowlisted")

        paths = data.get("test_paths", list(DEFAULT_TEST_PATHS))
        if (
            not isinstance(paths, list)
            or not paths
            or not all(isinstance(p, str) and p and ".." not in p for p in paths)
        ):
            raise ConfigError("test_paths must be a non-empty list of safe relative paths")

        protected = data.get("protected_paths", list(DEFAULT_PROTECTED_PATHS))
        if not isinstance(protected, list) or not all(isinstance(p, str) for p in protected):
            raise ConfigError("protected_paths must be a list of strings")

        timeout = data.get("timeout_seconds", 300)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 10 <= timeout <= 3600:
            raise ConfigError("timeout_seconds must be an integer between 10 and 3600")

        def extra_markers(key: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
            raw_markers = data.get(key, [])
            if not isinstance(raw_markers, list) or not all(
                isinstance(m, str) and m.strip() for m in raw_markers
            ):
                raise ConfigError(f"{key} must be a list of non-empty strings")
            # Custom markers are appended, never replacing the built-in ones, so
            # a policy cannot switch off the environment-error detection.
            return defaults + tuple(m.strip().lower() for m in raw_markers)

        return cls(
            command=tuple(command),
            test_paths=tuple(p.rstrip("/") for p in paths),
            protected_paths=tuple(protected),
            timeout_seconds=timeout,
            environment_markers=extra_markers("environment_markers", DEFAULT_ENVIRONMENT_MARKERS),
            assertion_markers=extra_markers("assertion_markers", DEFAULT_ASSERTION_MARKERS),
        )
