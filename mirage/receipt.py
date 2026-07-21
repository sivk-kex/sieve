"""Trusted local execution receipts for MIRAGE task artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any


class ManifestError(ValueError):
    """Artifact manifest violates MIRAGE pilot constraints."""


@dataclass(frozen=True)
class ClaimManifest:
    task_id: str
    command: tuple[str, ...]
    expected_output: str
    expected_hashes: dict[str, str]


@dataclass(frozen=True)
class Receipt:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    file_hashes: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "elapsed_seconds": self.elapsed_seconds,
            "file_hashes": self.file_hashes,
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"invalid JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise ManifestError(f"JSON object required: {path.name}")
    return value


def _validate_command(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ManifestError("command must be a non-empty string list")

    command = tuple(value)
    if command[0] not in {"python", "python3", Path(sys.executable).name}:
        raise ManifestError("only Python commands are allowed")

    for argument in command[1:]:
        if Path(argument).is_absolute() or PureWindowsPath(argument).is_absolute():
            raise ManifestError("absolute path is not allowed")
        if argument == ".." or "../" in argument or "..\\" in argument:
            raise ManifestError("parent path is not allowed")

    return command


def _validate_hashes(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ManifestError("expected_hashes must be an object")

    hashes: dict[str, str] = {}
    for relative_path, digest in value.items():
        if not isinstance(relative_path, str) or not isinstance(digest, str):
            raise ManifestError("expected_hashes must map strings to strings")
        if Path(relative_path).is_absolute() or PureWindowsPath(relative_path).is_absolute():
            raise ManifestError("absolute path is not allowed")
        if relative_path == ".." or "../" in relative_path or "..\\" in relative_path:
            raise ManifestError("parent path is not allowed")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ManifestError("expected_hashes must contain SHA-256 digests")
        hashes[relative_path] = digest
    return hashes


def load_manifest(path: Path) -> ClaimManifest:
    value = _read_json(path)
    task_id = value.get("id")
    expected_output = value.get("expected_output")
    if not isinstance(task_id, str) or not task_id:
        raise ManifestError("id must be a non-empty string")
    if not isinstance(expected_output, str) or not expected_output:
        raise ManifestError("expected_output must be a non-empty string")
    return ClaimManifest(
        task_id=task_id,
        command=_validate_command(value.get("command")),
        expected_output=expected_output,
        expected_hashes=_validate_hashes(value.get("expected_hashes")),
    )


def load_reproduction_command(path: Path) -> tuple[str, ...]:
    return _validate_command(_read_json(path).get("command"))


def _task_file(task_dir: Path, relative_path: str) -> Path:
    candidate = (task_dir / relative_path).resolve()
    try:
        candidate.relative_to(task_dir)
    except ValueError as error:
        raise ManifestError("path escapes task directory") from error
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_command(task_dir: Path, command: tuple[str, ...]) -> list[str]:
    if len(command) < 2:
        raise ManifestError("Python script path is required")
    script = _task_file(task_dir, command[1])
    if not script.is_file() or script.suffix != ".py":
        raise ManifestError("command must target a Python file in task directory")
    return [sys.executable, *command[1:]]


def run_task(
    task_dir: Path, manifest: ClaimManifest, timeout_seconds: float = 15.0
) -> Receipt:
    """Run reproduction command and capture trusted execution evidence."""
    task_dir = task_dir.resolve()
    command = load_reproduction_command(task_dir / "reproduction.json")
    executable_command = _prepare_command(task_dir, command)

    started = time.monotonic()
    try:
        completed = subprocess.run(
            executable_command,
            cwd=task_dir,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as error:
        exit_code = 124
        stdout = error.stdout or ""
        stderr = (error.stderr or "") + "\nMIRAGE timeout"
    elapsed_seconds = time.monotonic() - started

    file_hashes: dict[str, str | None] = {}
    for relative_path in manifest.expected_hashes:
        path = _task_file(task_dir, relative_path)
        file_hashes[relative_path] = _sha256(path) if path.is_file() else None

    return Receipt(
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        elapsed_seconds=elapsed_seconds,
        file_hashes=file_hashes,
    )
