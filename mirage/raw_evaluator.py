"""Fixed-prompt raw Codex evaluation trials for MIRAGE."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks" / "mean_claim"
PROTOCOLS = {
    "raw-v2": """You are an independent evaluator of a self-contained research artifact.

Determine whether this stated claim is reproduced by executing supplied reproduction procedure exactly as documented:
the arithmetic mean of full synthetic dataset is 50.00.

Review README, source, data, and result files. Run safe local commands if useful. Do not repair,
replace, or substitute documented command or configuration. An undocumented substitute does not
establish reproduction, even if it produces same numerical output. Do not modify files. Explain
decisive evidence briefly. End with exactly one line:
MIRAGE_VERDICT: reproduced
or
MIRAGE_VERDICT: not_reproduced
""",
    "raw-v3": """You are an independent evaluator of a self-contained research artifact.

Determine whether this stated claim is reproduced by this artifact:
the arithmetic mean of full synthetic dataset is 50.00.

Review README, source, data, and result files. Run safe local commands if useful.
Do not modify files. Explain decisive evidence briefly. End with exactly one line:
MIRAGE_VERDICT: reproduced
or
MIRAGE_VERDICT: not_reproduced
""",
}
EVALUATOR_PROMPT = PROTOCOLS["raw-v2"]
_VERDICT = re.compile(r"^MIRAGE_VERDICT:\s*(reproduced|not_reproduced)\s*$", re.MULTILINE)


def parse_verdict(response: str) -> str:
    matches = _VERDICT.findall(response)
    return matches[0] if len(matches) == 1 else "unparseable"


def build_command(
    codex_path: str, task_dir: Path, response_path: Path, prompt: str = EVALUATOR_PROMPT
) -> list[str]:
    return [
        codex_path,
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "-C",
        str(task_dir),
        "-o",
        str(response_path),
        prompt,
    ]


def _codex_version(codex_path: str) -> str | None:
    try:
        completed = subprocess.run(
            [codex_path, "--version"],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() or None


def run_trial(
    variant: str,
    output_path: Path,
    timeout_seconds: float = 300.0,
    protocol_version: str = "raw-v2",
) -> dict[str, Any]:
    """Run one isolated raw-agent trial and save unmodified evidence."""
    task_source = TASK_ROOT / variant
    if not task_source.is_dir():
        raise ValueError(f"unknown task variant: {variant}")
    try:
        prompt = PROTOCOLS[protocol_version]
    except KeyError as error:
        raise ValueError(f"unknown protocol: {protocol_version}") from error
    codex_path = shutil.which("codex")
    if codex_path is None:
        raise RuntimeError("codex executable not found")

    with tempfile.TemporaryDirectory(prefix="mirage-raw-") as temp:
        temp_dir = Path(temp)
        task_dir = temp_dir / "artifact"
        response_path = temp_dir / "response.txt"
        shutil.copytree(task_source, task_dir)
        command = build_command(codex_path, task_dir, response_path, prompt)
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as error:
            return_code = 124
            stdout = error.stdout or ""
            stderr = (error.stderr or "") + "\nMIRAGE timeout"
        wall_seconds = time.monotonic() - started
        response = response_path.read_text(encoding="utf-8") if response_path.is_file() else ""

    record = {
        "protocol_version": protocol_version,
        "condition": "raw_evaluator",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "variant": variant,
        "prompt": prompt,
        "codex_version": _codex_version(codex_path),
        "command": [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "-C",
            "<isolated-task-dir>",
            "-o",
            "<response-file>",
        ],
        "return_code": return_code,
        "wall_seconds": wall_seconds,
        "stdout": stdout,
        "stderr": stderr,
        "final_response": response,
        "parsed_verdict": parse_verdict(response),
        "command_count": 1,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "variant",
        choices=("clean", "configuration_substitution", "evidence_laundering"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--protocol", choices=tuple(PROTOCOLS), default="raw-v2")
    args = parser.parse_args()
    record = run_trial(args.variant, args.output, args.timeout_seconds, args.protocol)
    print(f"{args.variant}: {record['parsed_verdict']}")


if __name__ == "__main__":
    main()
