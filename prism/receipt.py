"""Summarize the narrow ambient inputs visible in a strace log."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping


_EXECVE = re.compile(r'execve\("(?P<path>(?:[^"\\]|\\.)*)",.*\)\s+=\s+0')
_OPENAT = re.compile(
    r'openat\([^,]+,\s+"(?P<path>(?:[^"\\]|\\.)*)",\s*'
    r'(?P<flags>[^)]*)\)\s+=\s+(?P<result>-?\d+)'
)


def _unescape_trace_path(path: str) -> str:
    return path.replace(r'\\', "\\").replace(r'\\\"', '"')


def _origin_for(path: str, repository: Path, ambient_roots: Mapping[str, Path]) -> str | None:
    candidate = Path(path)
    try:
        candidate.relative_to(repository)
        return None
    except ValueError:
        pass

    for origin, root in ambient_roots.items():
        try:
            candidate.relative_to(root)
            return origin
        except ValueError:
            continue
    return None


def summarize_trace(
    trace: str, *, repository: Path, ambient_roots: Mapping[str, Path]
) -> dict[str, list[dict[str, str]]]:
    """Return fixture-declared ambient executable and file-read inputs.

    This Stage-1 parser intentionally ignores system libraries and every path
    outside the fixture's declared ambient roots. It is not a whole-system
    provenance collector.
    """
    inputs: list[dict[str, str]] = []
    positions: dict[tuple[str, str], int] = {}

    def add(kind: str, path: str) -> None:
        origin = _origin_for(path, repository, ambient_roots)
        if origin is None:
            return
        key = (origin, path)
        position = positions.get(key)
        if position is None:
            positions[key] = len(inputs)
            inputs.append({"kind": kind, "origin": origin, "path": path})
        elif kind == "executable" and inputs[position]["kind"] != "executable":
            inputs[position]["kind"] = kind

    for line in trace.splitlines():
        execve = _EXECVE.search(line)
        if execve:
            add("executable", _unescape_trace_path(execve.group("path")))
            continue

        openat = _OPENAT.search(line)
        if openat and openat.group("result") != "-1" and "O_RDONLY" in openat.group("flags"):
            add("read", _unescape_trace_path(openat.group("path")))

    return {"ambient_inputs": inputs}
