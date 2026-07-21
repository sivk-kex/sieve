"""Load the small, controlled PRISM fixture contracts."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .receipt import summarize_trace


class FixtureError(ValueError):
    """Fixture metadata is malformed."""


_PARENT_VALUE = re.compile(r"\{parent:([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class Fixture:
    path: Path
    repository: Path
    command: tuple[str, ...]
    states: dict[str, dict[str, object]]

    def context_for(
        self, state: str, parent_environment: Mapping[str, str]
    ) -> tuple[dict[str, str], dict[str, Path]]:
        try:
            spec = self.states[state]
        except KeyError as error:
            raise FixtureError(f"unknown fixture state: {state}") from error

        environment = dict(parent_environment)
        raw_environment = spec.get("environment", {})
        if not isinstance(raw_environment, dict):
            raise FixtureError("state environment must be an object")
        for name, value in raw_environment.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise FixtureError("environment must map strings to strings")
            environment[name] = self._expand(value, parent_environment)

        raw_roots = spec.get("ambient_roots", {})
        if not isinstance(raw_roots, dict):
            raise FixtureError("ambient_roots must be an object")
        roots: dict[str, Path] = {}
        for origin, relative_path in raw_roots.items():
            if not isinstance(origin, str) or not isinstance(relative_path, str):
                raise FixtureError("ambient_roots must map strings to strings")
            root = (self.path / relative_path).resolve()
            try:
                root.relative_to(self.path)
            except ValueError as error:
                raise FixtureError("ambient root escapes fixture") from error
            roots[origin] = root
        return environment, roots

    def _expand(self, value: str, parent_environment: Mapping[str, str]) -> str:
        value = value.replace("{fixture}", str(self.path))
        value = value.replace("{repository}", str(self.repository))
        return _PARENT_VALUE.sub(
            lambda match: parent_environment.get(match.group(1), ""), value
        )


@dataclass(frozen=True)
class FixtureRun:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class TracedFixtureRun:
    run: FixtureRun
    receipt: dict[str, list[dict[str, str]]]
    trace: str


def _run_command(
    command: tuple[str, ...], repository: Path, environment: Mapping[str, str]
) -> FixtureRun:
    try:
        completed = subprocess.run(
            command,
            cwd=repository,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return FixtureRun(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    except subprocess.TimeoutExpired as error:
        return FixtureRun(
            command=command,
            exit_code=124,
            stdout=error.stdout or "",
            stderr=(error.stderr or "") + "\nPRISM fixture timeout",
        )


def run_fixture(
    fixture: Fixture, state: str, parent_environment: Mapping[str, str]
) -> FixtureRun:
    """Run a frozen fixture state without agent intervention."""
    environment, _ = fixture.context_for(state, parent_environment)
    return _run_command(fixture.command, fixture.repository, environment)


def run_traced_fixture(
    fixture: Fixture,
    state: str,
    parent_environment: Mapping[str, str],
    strace: Path,
) -> TracedFixtureRun:
    """Run one fixture through strace and summarize declared ambient inputs."""
    environment, roots = fixture.context_for(state, parent_environment)
    with tempfile.TemporaryDirectory(prefix="prism-trace-") as temp:
        trace_path = Path(temp) / "trace.log"
        traced_command = (
            str(strace),
            "-f",
            "-qq",
            "-o",
            str(trace_path),
            "-e",
            "trace=execve,openat",
            *fixture.command,
        )
        run = _run_command(traced_command, fixture.repository, environment)
        trace = trace_path.read_text(encoding="utf-8", errors="replace")

    return TracedFixtureRun(
        run=run,
        receipt=summarize_trace(
            trace,
            repository=fixture.repository,
            ambient_roots=roots,
        ),
        trace=trace,
    )


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
    states = data.get("states")
    if not isinstance(repository_name, str) or not repository_name:
        raise FixtureError("repository must be a non-empty string")
    if not isinstance(command, list) or not command or not all(
        isinstance(part, str) and part for part in command
    ):
        raise FixtureError("command must be a non-empty string list")
    if not isinstance(states, dict) or not states:
        raise FixtureError("states must be a non-empty object")

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
        states={name: value for name, value in states.items() if isinstance(name, str) and isinstance(value, dict)},
    )
