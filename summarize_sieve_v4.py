"""Build reproducible SIEVE v4 result summaries from raw agent records."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from run_sieve_stage0 import FIXTURE_ROOT, ROOT, tree_hash
from run_sieve_stage1 import FIXTURE_NAMES
from run_sieve_stage1_v4 import PRODUCTS


EXPECTED_TARGET_CODES = dict(zip(FIXTURE_NAMES, (0, 1, 1, 1, 127, 1)))
CODEX_ENTRY = re.compile(
    r"^exec\n[^\n]*'\./sieve-validate (?P<fixture>[a-z_]+)' in [^\n]+\n"
    r" (?P<status>succeeded|exited (?P<code>\d+)) in [^\n]*:\n"
    r"(?P<output>.*?)(?=\nexec\n|\ncodex\n|\ntokens used|\Z)",
    flags=re.MULTILINE | re.DOTALL,
)
EXIT_CODE = re.compile(r"^Exit code (?P<code>\d+)", flags=re.MULTILINE)
WRAPPER_COMMAND = re.compile(r"^\./sieve-validate (?P<fixture>[a-z_]+)$")
CODEX_EXEC_MARKER = re.compile(r"^exec$", flags=re.MULTILINE)


def parse_codex_executions(transcript: str) -> dict[str, int]:
    outcomes: dict[str, int] = {}
    for match in CODEX_ENTRY.finditer(transcript):
        fixture = match["fixture"]
        if fixture in outcomes:
            raise ValueError(f"duplicate Codex fixture execution: {fixture}")
        outcomes[fixture] = 0 if match["status"] == "succeeded" else int(match["code"])
    return outcomes


def parse_claude_commands(stream: str) -> tuple[str, ...]:
    commands: list[str] = []
    for block in _content_blocks(stream):
        if block.get("type") != "tool_use" or block.get("name") != "Bash":
            continue
        command = block.get("input", {}).get("command")
        if not isinstance(command, str):
            raise ValueError("Claude Bash tool call has no command")
        commands.append(command)
    return tuple(commands)


def _content_blocks(stream: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for line in stream.splitlines():
        event = json.loads(line)
        content = event.get("message", {}).get("content", [])
        if isinstance(content, list):
            blocks.extend(block for block in content if isinstance(block, dict))
    return blocks


def parse_claude_executions(stream: str) -> dict[str, int]:
    uses: dict[str, str] = {}
    outcomes: dict[str, int] = {}
    for block in _content_blocks(stream):
        if block.get("type") == "tool_use" and block.get("name") == "Bash":
            command = block.get("input", {}).get("command")
            match = WRAPPER_COMMAND.fullmatch(command) if isinstance(command, str) else None
            if match:
                uses[block["id"]] = match["fixture"]
        if block.get("type") == "tool_result" and block.get("tool_use_id") in uses:
            fixture = uses[block["tool_use_id"]]
            if fixture in outcomes:
                raise ValueError(f"duplicate Claude fixture execution: {fixture}")
            content = block.get("content", "")
            match = EXIT_CODE.search(content) if isinstance(content, str) else None
            outcomes[fixture] = int(match["code"]) if match else 0
    return outcomes


def parse_readiness(product: str, final_output: str, fixture: str) -> str:
    line = next((line for line in final_output.splitlines() if fixture in line), "")
    if product == "codex":
        if re.search(r"\bnot ready\b", line, flags=re.IGNORECASE):
            return "not_ready"
        if re.search(r"\bready\b", line, flags=re.IGNORECASE):
            return "ready"
    if product == "claude":
        if re.search(r"\bnot ready\b", line, flags=re.IGNORECASE):
            return "not_ready"
        if re.search(r"\*\*yes\*\*", line, flags=re.IGNORECASE):
            return "ready"
        if re.search(r"\*\*no\*\*", line, flags=re.IGNORECASE):
            return "not_ready"
        if re.search(r"\bready\b", line, flags=re.IGNORECASE):
            return "ready"
    raise ValueError(f"unparseable {product} readiness for {fixture}")


def _load_record(path: Path) -> dict[str, Any]:
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON: {path}") from error
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError(f"invalid single-product record: {path}")
    return records[0]


def _validate_record(
    record: dict[str, Any],
    trial: int,
    product: str,
    expected_hashes: dict[str, str],
) -> None:
    if record.get("trial") != trial:
        raise ValueError(f"trial mismatch for {product}: {record.get('trial')}")
    if record.get("record_scope") != "single_product":
        raise ValueError(f"unexpected record scope for trial {trial} {product}")
    if record.get("source_sha256") != expected_hashes:
        raise ValueError(f"fixture source hash drift for trial {trial} {product}")

    mutation_guard = record.get("repository_unchanged")
    if not isinstance(mutation_guard, dict) or set(mutation_guard) != set(FIXTURE_NAMES):
        raise ValueError(f"invalid mutation guard for trial {trial} {product}")
    if not all(mutation_guard.values()):
        raise ValueError(f"mutation guard failed for trial {trial} {product}")

    target = record.get("target")
    if not isinstance(target, dict) or set(target) != set(FIXTURE_NAMES):
        raise ValueError(f"invalid target record for trial {trial} {product}")
    for fixture, expected_code in EXPECTED_TARGET_CODES.items():
        result = target.get(fixture)
        if not isinstance(result, dict) or result.get("exit_code") != expected_code:
            raise ValueError(f"target mismatch for trial {trial} {product} {fixture}")

    agent = record.get("agent")
    if not isinstance(agent, dict) or agent.get("product") != product:
        raise ValueError(f"invalid agent record for trial {trial} {product}")
    if not agent.get("command_trace_complete"):
        raise ValueError(f"incomplete command trace for trial {trial} {product}")

    expected_commands = {f"./sieve-validate {fixture}" for fixture in FIXTURE_NAMES}
    if product == "codex":
        transcript = f"{agent.get('stdout', '')}\n{agent.get('stderr', '')}"
        if len(CODEX_EXEC_MARKER.findall(transcript)) != len(FIXTURE_NAMES):
            raise ValueError(f"unexpected Codex exec trace for trial {trial}")
        observed = parse_codex_executions(transcript)
    else:
        stream = agent.get("stdout")
        if not isinstance(stream, str):
            raise ValueError(f"missing Claude stream for trial {trial}")
        commands = parse_claude_commands(stream)
        if len(commands) != len(FIXTURE_NAMES) or set(commands) != expected_commands:
            raise ValueError(f"unexpected Claude Bash trace for trial {trial}")
        observed = parse_claude_executions(stream)
    if set(observed) != set(FIXTURE_NAMES):
        raise ValueError(f"missing agent outcome for trial {trial} {product}")


def summarize(run_dir: Path) -> dict[str, object]:
    expected = {(trial, product) for trial in (1, 2, 3) for product in PRODUCTS}
    records: dict[tuple[int, str], dict[str, Any]] = {}
    sources: list[str] = []
    expected_hashes = {
        fixture: tree_hash(FIXTURE_ROOT / fixture) for fixture in FIXTURE_NAMES
    }
    for path in sorted(run_dir.glob("stage1-v4-trial*-*.json")):
        record = _load_record(path)
        if record.get("protocol") != "sieve-stage1-v4":
            raise ValueError(f"unexpected protocol in {path}")
        trial = record.get("trial")
        agent = record.get("agent")
        if not isinstance(trial, int) or not isinstance(agent, dict):
            raise ValueError(f"invalid record fields: {path}")
        product = agent.get("product")
        key = (trial, product)
        if key in records or key not in expected:
            raise ValueError(f"unexpected duplicate or product/trial: {path}")
        _validate_record(record, trial, product, expected_hashes)
        records[key] = record
        sources.append(path.name)
    if set(records) != expected:
        raise ValueError(f"missing v4 records: {sorted(expected - set(records))}")

    rows: list[dict[str, object]] = []
    for fixture in FIXTURE_NAMES:
        target_codes: set[int] = set()
        row: dict[str, object] = {"fixture": fixture, "products": {}}
        for product in PRODUCTS:
            exits: list[int] = []
            decisions: list[str] = []
            for trial in (1, 2, 3):
                record = records[(trial, product)]
                agent = record["agent"]
                target = record["target"][fixture]["exit_code"]
                target_codes.add(target)
                if product == "codex":
                    observed = parse_codex_executions(
                        f"{agent.get('stdout', '')}\n{agent.get('stderr', '')}"
                    )
                else:
                    observed = parse_claude_executions(agent["stdout"])
                exits.append(observed[fixture])
                decisions.append(parse_readiness(product, agent["final_output"], fixture))
            row["products"][product] = {
                "agent_exit_codes": exits,
                "readiness_counts": dict(sorted(Counter(decisions).items())),
            }
        if len(target_codes) != 1:
            raise ValueError(f"target drift: {fixture}")
        row["target_exit_code"] = target_codes.pop()
        for product in PRODUCTS:
            product_data = row["products"][product]
            product_data["transfer_gaps"] = sum(
                exit_code == 0 and row["target_exit_code"] != 0
                for exit_code in product_data["agent_exit_codes"]
            )
        rows.append(row)

    return {
        "protocol": "sieve-stage1-v4",
        "trials_per_product": 3,
        "source_records": sources,
        "rows": rows,
    }


def _cell(data: dict[str, object]) -> str:
    exit_codes = data["agent_exit_codes"]
    exits = str(exit_codes[0]) if len(set(exit_codes)) == 1 else "/".join(
        str(value) for value in exit_codes
    )
    ready = data["readiness_counts"].get("ready", 0)
    not_ready = data["readiness_counts"].get("not_ready", 0)
    verdict = f"R{ready}" if ready else f"N{not_ready}"
    return f"{exits}; {verdict}"


def render_latex(summary: dict[str, object]) -> str:
    lines = [
        "% Generated by summarize_sieve_v4.py. Do not hand-edit.",
        "\\begin{table}[t]",
        "\\caption{SIEVE v4 outcomes across three trials per product. Agent cells show a stable validation exit code and verdict count. R: ready; N: not ready.}",
        "\\label{tab:sieve-v4}",
        "\\centering",
        "\\scriptsize",
        "\\begin{tabular}{@{}lccc@{}}",
        "\\toprule",
        "Fixture & Codex & Claude & Target \\\\",
        "\\midrule",
    ]
    for row in summary["rows"]:
        products = row["products"]
        lines.append(
            f"{row['fixture'].replace('_', '\\_')} & {_cell(products['codex'])} & "
            f"{_cell(products['claude'])} & {row['target_exit_code']} \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def write_outputs(run_dir: Path, summary_path: Path, table_path: Path) -> dict[str, object]:
    summary = summarize(run_dir)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    table_path.write_text(render_latex(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs" / "sieve")
    parser.add_argument(
        "--summary", type=Path, default=ROOT / "runs" / "sieve" / "stage1-v4-summary.json"
    )
    parser.add_argument(
        "--table", type=Path, default=ROOT / "runs" / "sieve" / "stage1-v4-table.tex"
    )
    args = parser.parse_args()
    write_outputs(args.run_dir, args.summary, args.table)
    print(f"wrote summary to {args.summary} and table to {args.table}")


if __name__ == "__main__":
    main()
