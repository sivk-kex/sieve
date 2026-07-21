"""Load and execute SIEVE's deterministic validation fixtures."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class FixtureError(ValueError):
    """A SIEVE fixture is incomplete."""


@dataclass(frozen=True)
class Fixture:
    path: Path
    repository: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class FixtureRun:
    exit_code: int
    stdout: str
    stderr: str


def load_fixture(path: Path) -> Fixture:
    path = path.resolve()
    repository = path / "repo"
    command = repository / "run-validation"
    if not repository.is_dir() or not command.is_file():
        raise FixtureError(f"invalid fixture: {path}")
    return Fixture(path=path, repository=repository, command=("sh", "run-validation"))


def run_command(fixture: Fixture, environment: Mapping[str, str]) -> FixtureRun:
    try:
        completed = subprocess.run(
            fixture.command,
            cwd=fixture.repository,
            env=dict(environment),
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return FixtureRun(124, stdout, f"{stderr}\nfixture timeout")
    return FixtureRun(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_target(fixture: Fixture) -> FixtureRun:
    """Execute the fixture without any caller-state marker."""
    return run_command(fixture, {"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
