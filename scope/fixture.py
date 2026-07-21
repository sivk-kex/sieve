"""Load and execute the caller plane for SCOPE fixtures."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class FixtureError(ValueError):
    """Fixture metadata is malformed."""


_PARENT_VALUE = re.compile(r"\{parent:([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class Fixture:
    path: Path
    repository: Path
    command: tuple[str, ...]
    caller_environment: dict[str, str]
    scope_card: dict[str, object]

    def caller_context(self, parent_environment: Mapping[str, str]) -> dict[str, str]:
        environment = dict(parent_environment)
        for name, value in self.caller_environment.items():
            environment[name] = self._expand(value, parent_environment)
        return environment

    def _expand(self, value: str, parent_environment: Mapping[str, str]) -> str:
        value = value.replace("{fixture}", str(self.path))
        value = value.replace("{repository}", str(self.repository))
        return _PARENT_VALUE.sub(
            lambda match: parent_environment.get(match.group(1), ""), value
        )


@dataclass(frozen=True)
class FixtureRun:
    exit_code: int
    stdout: str
    stderr: str


def load_fixture(path: Path) -> Fixture:
    path = path.resolve()
    try:
        data = json.loads((path / "fixture.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FixtureError(f"invalid fixture: {path}") from error
    if not isinstance(data, dict):
        raise FixtureError("fixture must be an object")

    repository_name = data.get("repository")
    command = data.get("command")
    caller = data.get("caller")
    scope_card = data.get("scope_card")
    if not isinstance(repository_name, str) or not repository_name:
        raise FixtureError("repository must be a non-empty string")
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) and part for part in command
    ):
        raise FixtureError("command must be a non-empty string list")
    if not isinstance(caller, dict) or not isinstance(
        caller.get("environment"), dict
    ):
        raise FixtureError("caller environment is required")
    if not isinstance(scope_card, dict):
        raise FixtureError("scope_card is required")

    caller_environment = caller["environment"]
    if not all(
        isinstance(name, str) and isinstance(value, str)
        for name, value in caller_environment.items()
    ):
        raise FixtureError("caller environment must map strings to strings")

    repository = (path / repository_name).resolve()
    try:
        repository.relative_to(path)
    except ValueError as error:
        raise FixtureError("repository escapes fixture") from error
    if not repository.is_dir():
        raise FixtureError("repository directory is missing")

    return Fixture(
        path=path,
        repository=repository,
        command=tuple(command),
        caller_environment=dict(caller_environment),
        scope_card=dict(scope_card),
    )


def run_caller_fixture(
    fixture: Fixture, parent_environment: Mapping[str, str]
) -> FixtureRun:
    """Run the command in the caller's controlled plane."""
    completed = subprocess.run(
        fixture.command,
        cwd=fixture.repository,
        env=fixture.caller_context(parent_environment),
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return FixtureRun(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
