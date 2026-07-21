"""Summarize raw evaluator trials against deterministic receipt outcomes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
KNOWN_VERDICTS = {"reproduced", "not_reproduced", "unparseable"}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid JSON: {path}") from error


def _receipt_verdicts(receipt_path: Path) -> dict[str, str]:
    records = _load_json(receipt_path)
    if not isinstance(records, list):
        raise ValueError("receipt record must be a list")

    verdicts: dict[str, str] = {}
    for record in records:
        try:
            variant = record["variant"]
            reproduced = record["deterministic_verdict"]["reproduced"]
        except (KeyError, TypeError) as error:
            raise ValueError("invalid receipt record") from error
        if not isinstance(variant, str) or not isinstance(reproduced, bool):
            raise ValueError("invalid receipt record")
        if variant in verdicts:
            raise ValueError(f"duplicate receipt variant: {variant}")
        verdicts[variant] = "reproduced" if reproduced else "not_reproduced"
    return verdicts


def summarize_run_directory(raw_dir: Path, receipt_path: Path) -> dict[str, object]:
    """Return an auditable summary of raw trials against receipt outcomes."""
    receipt_verdicts = _receipt_verdicts(receipt_path)
    grouped: dict[str, list[dict[str, object]]] = {}
    protocol_versions: set[str] = set()

    for path in sorted(raw_dir.glob("*/trial-*.json")):
        record = _load_json(path)
        if not isinstance(record, dict):
            raise ValueError(f"raw record is not an object: {path}")
        variant = record.get("variant")
        verdict = record.get("parsed_verdict")
        protocol_version = record.get("protocol_version")
        wall_seconds = record.get("wall_seconds")
        if not isinstance(variant, str) or variant not in receipt_verdicts:
            raise ValueError(f"missing receipt verdict for raw variant: {variant}")
        if verdict not in KNOWN_VERDICTS:
            raise ValueError(f"invalid raw verdict in {path}: {verdict}")
        if not isinstance(protocol_version, str):
            raise ValueError(f"missing protocol version in {path}")
        if not isinstance(wall_seconds, (int, float)):
            raise ValueError(f"invalid wall time in {path}")
        protocol_versions.add(protocol_version)
        grouped.setdefault(variant, []).append(
            {"verdict": verdict, "wall_seconds": float(wall_seconds), "path": path.as_posix()}
        )

    if not grouped:
        raise ValueError(f"no raw trials found in {raw_dir}")
    if len(protocol_versions) != 1:
        raise ValueError(f"mixed protocol versions: {sorted(protocol_versions)}")

    variants: dict[str, object] = {}
    for variant, records in sorted(grouped.items()):
        receipt_verdict = receipt_verdicts[variant]
        outcomes = Counter()
        for record in records:
            verdict = record["verdict"]
            if verdict == "unparseable":
                outcomes["unparseable"] += 1
            elif verdict == receipt_verdict:
                outcomes["matches_receipt"] += 1
            elif verdict == "reproduced":
                outcomes["receipt_disagreement_positive"] += 1
            else:
                outcomes["receipt_disagreement_negative"] += 1
        variants[variant] = {
            "receipt_verdict": receipt_verdict,
            "trials": len(records),
            "verdict_counts": {
                verdict: sum(record["verdict"] == verdict for record in records)
                for verdict in sorted(KNOWN_VERDICTS)
            },
            "outcomes": {
                key: outcomes[key]
                for key in (
                    "matches_receipt",
                    "receipt_disagreement_positive",
                    "receipt_disagreement_negative",
                    "unparseable",
                )
            },
            "mean_wall_seconds": sum(record["wall_seconds"] for record in records) / len(records),
            "source_records": [record["path"] for record in records],
        }

    return {
        "protocol_version": next(iter(protocol_versions)),
        "receipt_source": receipt_path.as_posix(),
        "raw_source": raw_dir.as_posix(),
        "total_trials": sum(len(records) for records in grouped.values()),
        "variants": variants,
    }


def write_summary(raw_dir: Path, receipt_path: Path, output_path: Path) -> dict[str, object]:
    summary = summarize_run_directory(raw_dir, receipt_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "runs" / "raw-v3")
    parser.add_argument("--receipt", type=Path, default=ROOT / "runs" / "receipt" / "pilot.json")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "runs" / "summary" / "raw-v3-summary.json"
    )
    args = parser.parse_args()
    summary = write_summary(args.raw_dir, args.receipt, args.output)
    print(f"wrote {summary['total_trials']} trials to {args.output}")


if __name__ == "__main__":
    main()
