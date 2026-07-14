"""Run authenticated SIEVE Stage 1 v3 one trial at a time."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

from run_sieve_stage0 import ROOT, tree_hash
from run_sieve_stage1 import FIXTURE_NAMES, copy_workspace, parse_trial, stage1_environment
from run_sieve_stage1_v2 import (
    CLAUDE_MODEL,
    WRAPPER_NAME,
    complete_wrapper_trace,
    create_validator_wrapper,
    final_output_from_stream,
    prompt_for,
    run_codex,
    trace_commands,
)
from sieve.fixture import run_target


def claude_command(workspace: Path, prompt: str) -> list[str]:
    executable = shutil.which("claude")
    if not executable:
        raise RuntimeError("claude CLI is unavailable")
    return [
        executable,
        "--print",
        "--safe-mode",
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--tools",
        "Bash",
        "--allowed-tools",
        f"Bash(./{WRAPPER_NAME}:*)",
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-budget-usd",
        "0.50",
        "--effort",
        "low",
        "--model",
        CLAUDE_MODEL,
        prompt,
    ]


def run_claude(
    workspace: Path,
    environment: Mapping[str, str],
    prompt: str,
    parent_environment: Mapping[str, str],
) -> dict[str, object]:
    environment = {
        **environment,
        "HOME": parent_environment.get("HOME", str(Path.home())),
    }
    command = claude_command(workspace, prompt)
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=environment,
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        commands = trace_commands(completed.stdout)
        return {
            "product": "claude",
            "model": CLAUDE_MODEL,
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "final_output": final_output_from_stream(completed.stdout),
            "executed_commands": commands,
            "command_trace_complete": complete_wrapper_trace(commands),
        }
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        stderr = error.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "product": "claude",
            "model": CLAUDE_MODEL,
            "command": command,
            "exit_code": 124,
            "stdout": stdout,
            "stderr": f"{stderr}\nagent timeout",
            "final_output": final_output_from_stream(stdout),
            "executed_commands": trace_commands(stdout),
            "command_trace_complete": False,
        }


def run_product(
    product: str, trial: int, parent_environment: Mapping[str, str]
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"sieve-stage1-v3-{product}-") as temporary:
        workspace = Path(temporary) / "candidates"
        workspace.mkdir()
        fixtures, source_hashes = copy_workspace(workspace)
        create_validator_wrapper(workspace)
        environment = stage1_environment(parent_environment, workspace)
        before_hashes = {
            name: tree_hash(fixture.repository) for name, fixture in fixtures.items()
        }
        prompt = prompt_for()
        if product == "codex":
            agent = run_codex(workspace, environment, prompt)
        elif product == "claude":
            agent = run_claude(workspace, environment, prompt, parent_environment)
        else:
            raise ValueError(f"unknown product: {product}")
        after_hashes = {
            name: tree_hash(fixture.repository) for name, fixture in fixtures.items()
        }
        target = {name: run_target(fixture) for name, fixture in fixtures.items()}
        return {
            "protocol": "sieve-stage1-v3",
            "trial": trial,
            "recorded_at": datetime.now(UTC).isoformat(),
            "source_sha256": source_hashes,
            "synthetic_state": {
                "release_token": "present",
                "config_marker": "present",
                "path_marker": "present",
                "cwd_marker": "present",
            },
            "repository_unchanged": {
                name: before_hashes[name] == after_hashes[name] for name in FIXTURE_NAMES
            },
            "target": {
                name: {
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
                for name, result in target.items()
            },
            "agent": agent,
        }


def default_output_path(trial: int) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "runs" / "sieve" / f"stage1-v3-trial{trial}-{timestamp}.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial", required=True, type=parse_trial)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    records = [
        run_product(product, args.trial, os.environ) for product in ("codex", "claude")
    ]
    output_path = args.output or default_output_path(args.trial)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(records)} Stage-1 v3 records to {output_path}")


if __name__ == "__main__":
    main()
