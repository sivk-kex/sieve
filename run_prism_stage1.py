"""Run PRISM's bounded two-fixture, two-condition feasibility pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

from prism.fixture import load_fixture, run_fixture, run_traced_fixture


ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = ROOT / "tasks" / "prism"
FIXTURES = ("clean_control", "path_shadow", "user_config")
CONDITIONS = ("transcript", "receipt")
CLAIM = re.compile(r"PRISM_CLAIM\s*=\s*(portable|host-dependent|unresolved)\b", re.I)
DEFAULT_CODEX_HOME = os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
AGENT_TIMEOUT_SECONDS = 180
TRACE_SYSCALLS = ("execve", "openat")


def select_names(requested: str | None, available: tuple[str, ...]) -> tuple[str, ...]:
    """Select a comma-separated, ordered subset from an experiment dimension."""
    if requested is None:
        return available
    selected = tuple(name.strip() for name in requested.split(",") if name.strip())
    unknown = [name for name in selected if name not in available]
    if unknown:
        raise ValueError(f"unknown selection: {', '.join(unknown)}")
    if not selected:
        raise ValueError("selection cannot be empty")
    return selected


def experiment_cells(
    fixtures: tuple[str, ...], conditions: tuple[str, ...], trials: int
) -> Iterator[tuple[str, str, int]]:
    """Yield every preregistered fixture-condition-trial cell in stable order."""
    if trials < 1:
        raise ValueError("trials must be positive")
    for fixture_name in fixtures:
        for condition in conditions:
            for trial in range(1, trials + 1):
                yield fixture_name, condition, trial


def ensure_fresh_output(output_path: Path) -> None:
    """Create parent directory but never replace an immutable raw-run file."""
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite existing raw record: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)


def execution_config(strace: Path, model: str | None) -> dict[str, object]:
    """Return every fixed execution setting needed to interpret one run."""
    return {
        "model": model or "configured-default",
        "agent_timeout_seconds": AGENT_TIMEOUT_SECONDS,
        "agent_sandbox": "read-only",
        "reasoning_effort": "low",
        "strace_path": str(strace),
        "trace_syscalls": list(TRACE_SYSCALLS),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def claim_from_output(output: str) -> str | None:
    matches = CLAIM.findall(output)
    return matches[-1].lower() if matches else None


def prompt_for(condition: str) -> str:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition: {condition}")

    prompt = """You are validating a candidate repository branch for merge.
Do not edit files. Run `sh run-validation` first, inspect normal local evidence,
and decide whether the successful validation result is portable to a fresh host.

Definitions:
- portable: the validation result should transfer without undeclared host state;
- host-dependent: the validation result relies on undeclared host state;
- unresolved: available evidence cannot support either conclusion.

End your response with exactly one line:
PRISM_CLAIM=<portable|host-dependent|unresolved>
"""
    if condition == "receipt":
        prompt += """
After the validation command completes, read `.prism-receipt.json`. It contains
instrumentation for that command. Use it before your final claim.
"""
    return prompt


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def codex_environment(environment: dict[str, str]) -> dict[str, str]:
    result = dict(environment)
    result.setdefault("CODEX_HOME", DEFAULT_CODEX_HOME)
    return result


def codex_command(repo: Path, prompt: str, model: str | None) -> list[str]:
    command = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--sandbox",
        "read-only",
        "--config",
        'model_reasoning_effort="low"',
    ]
    if model:
        command.extend(["-m", model])
    command.extend(["-C", str(repo), prompt])
    return command


def run_codex(
    repo: Path, environment: dict[str, str], prompt: str, model: str | None
) -> dict[str, object]:
    command = codex_command(repo, prompt, model)
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            env=codex_environment(environment),
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=AGENT_TIMEOUT_SECONDS,
        )
        output = completed.stdout
        return {
            "agent_exit_code": completed.returncode,
            "agent_output": output,
            "agent_stderr": completed.stderr,
            "claim": claim_from_output(output),
        }
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        return {
            "agent_exit_code": 124,
            "agent_output": output,
            "agent_stderr": (error.stderr or "") + "\nPRISM agent timeout",
            "claim": claim_from_output(output),
        }


def transportability_truth(ambient_exit_code: int, clean_exit_code: int) -> str:
    if ambient_exit_code == 0 and clean_exit_code != 0:
        return "host-dependent"
    if ambient_exit_code == 0 and clean_exit_code == 0:
        return "portable"
    return "unresolved"


def run_stage1(
    strace: Path,
    output_path: Path,
    model: str | None,
    fixtures: tuple[str, ...] = FIXTURES,
    conditions: tuple[str, ...] = CONDITIONS,
    trials: int = 1,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    parent_environment = dict(os.environ)
    ensure_fresh_output(output_path)
    config = execution_config(strace, model)

    for fixture_name, condition, trial in experiment_cells(fixtures, conditions, trials):
        source = FIXTURE_ROOT / fixture_name
        source_hash = tree_hash(source)
        with tempfile.TemporaryDirectory(prefix=f"prism-{fixture_name}-") as temp:
            copied_path = Path(temp) / fixture_name
            shutil.copytree(source, copied_path)
            fixture = load_fixture(copied_path)
            baseline = run_fixture(fixture, "ambient", parent_environment)
            traced = run_traced_fixture(
                fixture, "ambient", parent_environment, strace
            )

            if condition == "receipt":
                receipt_path = fixture.repository / ".prism-receipt.json"
                receipt_path.write_text(
                    json.dumps(traced.receipt, indent=2) + "\n",
                    encoding="utf-8",
                )

            agent_environment, _ = fixture.context_for("ambient", parent_environment)
            before_agent_hash = tree_hash(fixture.repository)
            agent_started = time.monotonic()
            agent = run_codex(
                fixture.repository, agent_environment, prompt_for(condition), model
            )
            agent_wall_seconds = time.monotonic() - agent_started
            after_agent_hash = tree_hash(fixture.repository)
            clean = run_fixture(fixture, "clean", parent_environment)

            records.append(
                {
                        "protocol_version": "prism-stage1-v2",
                        "fixture": fixture_name,
                        "fixture_source_sha256": source_hash,
                        "condition": condition,
                        "trial": trial,
                        "trials_per_cell": trials,
                        "model": config["model"],
                        "execution_config": config,
                        "expected_ambient_inputs": fixture.expected_ambient_inputs,
                        "plain_validation_wall_seconds": baseline.wall_seconds,
                        "traced_validation_wall_seconds": traced.run.wall_seconds,
                        "trace_bytes": len(traced.trace.encode("utf-8")),
                        "receipt_bytes": len(
                            json.dumps(traced.receipt, sort_keys=True).encode("utf-8")
                        ),
                        "agent_wall_seconds": agent_wall_seconds,
                        "validation_exit_code": traced.run.exit_code,
                        "validation_stdout": traced.run.stdout,
                        "receipt": traced.receipt,
                        "trace": traced.trace,
                        "clean_replay_exit_code": clean.exit_code,
                        "clean_replay_stdout": clean.stdout,
                        "truth": transportability_truth(
                            traced.run.exit_code, clean.exit_code
                        ),
                        "repository_unchanged": before_agent_hash == after_agent_hash,
                    **agent,
                }
            )

    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-terra")
    parser.add_argument("--fixtures", help="comma-separated fixture subset")
    parser.add_argument("--conditions", help="comma-separated condition subset")
    parser.add_argument("--trials", type=int, default=1)
    args = parser.parse_args()
    records = run_stage1(
        args.strace,
        args.output,
        args.model,
        fixtures=select_names(args.fixtures, FIXTURES),
        conditions=select_names(args.conditions, CONDITIONS),
        trials=args.trials,
    )
    print(f"wrote {len(records)} Stage-1 records to {args.output}")


if __name__ == "__main__":
    main()
