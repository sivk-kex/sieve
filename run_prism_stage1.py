"""Run PRISM's bounded two-fixture, two-condition feasibility pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from prism.fixture import load_fixture, run_fixture, run_traced_fixture


ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = ROOT / "tasks" / "prism"
FIXTURES = ("path_shadow", "user_config")
CONDITIONS = ("transcript", "receipt")
CLAIM = re.compile(r"PRISM_CLAIM\s*=\s*(portable|host-dependent|unresolved)\b", re.I)
DEFAULT_CODEX_HOME = os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))


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
            timeout=180,
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
    strace: Path, output_path: Path, model: str | None
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    parent_environment = dict(os.environ)

    for fixture_name in FIXTURES:
        source = FIXTURE_ROOT / fixture_name
        source_hash = tree_hash(source)
        for condition in CONDITIONS:
            with tempfile.TemporaryDirectory(prefix=f"prism-{fixture_name}-") as temp:
                copied_path = Path(temp) / fixture_name
                shutil.copytree(source, copied_path)
                fixture = load_fixture(copied_path)
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
                agent = run_codex(
                    fixture.repository, agent_environment, prompt_for(condition), model
                )
                after_agent_hash = tree_hash(fixture.repository)
                clean = run_fixture(fixture, "clean", parent_environment)

                records.append(
                    {
                        "fixture": fixture_name,
                        "fixture_source_sha256": source_hash,
                        "condition": condition,
                        "model": model or "configured-default",
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strace", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "prism" / "stage1.json")
    parser.add_argument("--model", default="gpt-5.6-terra")
    args = parser.parse_args()
    records = run_stage1(args.strace, args.output, args.model)
    print(f"wrote {len(records)} Stage-1 records to {args.output}")


if __name__ == "__main__":
    main()
