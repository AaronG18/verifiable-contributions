from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest

from vrc.config import Config, ConfigError


def _policy(command: list[str], **extra: object) -> bytes:
    fields: dict[str, object] = {
        "command": command,
        "test_paths": ["tests/"],
    }
    fields.update(extra)
    return (
        "\n".join(f"{key} = {json.dumps(value)}" for key, value in fields.items()) + "\n"
    ).encode("utf-8")


def test_default_policy_is_safe() -> None:
    config = Config.default()
    assert config.command[0] == "python"
    assert config.timeout_seconds == 300
    assert ".vrc.toml" in config.protected_paths


def test_security_config_files_are_protected_by_default() -> None:
    config = Config.default()
    assert ".github/dependabot.yml" in config.protected_paths
    assert "SECURITY.md" in config.protected_paths


def test_repo_policy_matches_the_default_protected_paths() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    data = tomllib.loads((repo_root / ".vrc.toml").read_text(encoding="utf-8"))
    assert tuple(data["protected_paths"]) == Config.default().protected_paths


def test_load_accepts_interpreter_absolute_path() -> None:
    config = Config.load(_policy([sys.executable, "-m", "pytest", "-q"]))
    assert config.command[0] == sys.executable


def test_rejects_non_allowlisted_executable() -> None:
    with pytest.raises(ConfigError, match="not allowlisted"):
        Config.load(_policy(["rm", "-rf", "/"]))


def test_rejects_empty_command() -> None:
    with pytest.raises(ConfigError, match="non-empty list"):
        Config.load(_policy([]))


def test_rejects_shell_string() -> None:
    with pytest.raises(ConfigError, match="non-empty list"):
        Config.load(b'command = "python -m pytest && curl evil.example"\n')


def test_rejects_path_traversal_in_test_paths() -> None:
    with pytest.raises(ConfigError, match="test_paths"):
        Config.load(_policy(["python"], test_paths=["../outside"]))


def test_rejects_bad_timeout() -> None:
    with pytest.raises(ConfigError, match="timeout_seconds"):
        Config.load(_policy(["python"], timeout_seconds=1))


def test_rejects_malformed_toml() -> None:
    with pytest.raises(ConfigError, match="invalid"):
        Config.load(b"this is not toml = [\n")


def test_missing_file_raises() -> None:
    with pytest.raises(ConfigError, match="not found"):
        Config.load(Path("/definitely/not/here/.vrc.toml"))


def test_protected_paths_are_respected() -> None:
    config = Config.load(_policy(["python"], protected_paths=["vrc/", "custom.yml"]))
    assert config.protected_paths == ("vrc/", "custom.yml")
